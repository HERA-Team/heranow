import os
import redis
import numpy as np
from astropy.time import Time
from argparse import Namespace
from django.utils import timezone

from celery.decorators import task
from celery.utils.log import get_task_logger
from celery.task.schedules import crontab
from celery.decorators import periodic_task

from hera_mc import mc, cm_sysutils, cm_utils, cm_sysdef, cm_hookup
from hera_mc.correlator import _pam_fem_serial_list_to_string

from hera_corr_cm import HeraCorrCM

from heranow import settings
from dashboard.models import (
    Antenna,
    AntennaStatus,
    AutoSpectra,
    SnapSpectra,
    SnapStatus,
    HookupNotes,
)

logger = get_task_logger(__name__)


@periodic_task(
    run_every=(crontab(minute="*/1")), name="get_autos_from_redis", ignore_result=True,
)
def get_autospectra_from_redis():
    logger.info("Getting AutoSpectra from Redis")
    redis_pool = redis.ConnectionPool(host="redishost", port=6379)
    with redis.Redis(connection_pool=redis_pool) as rsession:
        for antenna in Antenna.objects.all():
            d = rsession.get(f"auto:{antenna.ant_number:d}{antenna.polarization:s}")
            if d is not None:
                auto = np.frombuffer(d, dtype=np.float32).copy()
                break
        auto_size = auto.size
        # Generate frequency axis
        # Some times we have 6144 length inputs, others 1536, this should
        # set the length to match whatever the auto we got was
        NCHANS = int(8192 // 4 * 3)
        NCHANS_F = 8192
        NCHAN_SUM = NCHANS // auto_size
        NCHANS = auto_size
        frange = np.linspace(0, 250e6, NCHANS_F + 1)[1536 : 1536 + (8192 // 4 * 3)]
        # average over channels
        freqs = frange.reshape(NCHANS, NCHAN_SUM).sum(axis=1) / NCHAN_SUM

        timestamp = np.frombuffer(rsession["auto:timestamp"], dtype=np.float64)[0]
        timestamp = Time(timestamp, format="jd")
        timestamp = timestamp.datetime

        spectra = []
        for antenna in Antenna.objects.all():
            d = rsession.get(f"auto:{antenna.ant_number:d}{antenna.polarization:s}")
            if d is not None:
                auto = np.frombuffer(d, dtype=np.float32)[0:NCHANS].copy()

                eq_coeffs = rsession.hget(
                    f"eq:ant:{antenna.ant_number:d}{antenna.polarization:s}".encode(),
                    "values",
                )
                if eq_coeffs is not None:
                    eq_coeffs = np.fromstring(
                        eq_coeffs.decode("utf-8").strip("[]"), sep=","
                    )
                    if eq_coeffs.size == 0:
                        eq_coeffs = np.ones_like(auto)
                else:
                    eq_coeffs = np.ones_like(auto)

                auto_spectra = AutoSpectra(
                    antenna=antenna,
                    spectra=auto.tolist(),
                    frequencies=freqs.tolist(),
                    time=timestamp,
                    eq_coeffs=eq_coeffs.tolist(),
                )
                spectra.append(auto_spectra)

        AutoSpectra.objects.bulk_create(spectra, ignore_conflicts=True)
    logger.info("Done")
    return


@periodic_task(
    run_every=(crontab(minute="*/1")), name="get_snap_spectra", ignore_result=True,
)
def get_snap_spectra_from_redis():
    logger.info("Getting Snap Spectra from Redis")
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)
    snap_spectra = corr_cm.get_snaprf_status()
    spectra_list = []
    for snap_key, stats in snap_spectra.items():
        for key in stats:
            if stats[key] == "None":
                stats[key] = None
        hostname, input_number = snap_key.split(":")
        spectra = SnapSpectra(
            hostname=hostname,
            input_number=input_number,
            time=stats["timestamp"],
            spectra=stats["autocorrelation"],
            eq_coeffs=stats["eq_coeffs"],
            adc_hist=stats["histogram"],
        )
        spectra_list.append(spectra)

    SnapSpectra.objects.bulk_create(spectra_list, ignore_conflicts=True)
    logger.info("Done")
    return


@periodic_task(
    run_every=(crontab(minute="*/1")), name="get_snap_status", ignore_result=True,
)
def get_snap_status_from_redis():
    logger.info("Getting Snap Status from Redis")
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)

    snap_status = corr_cm.get_f_status()

    db = mc.connect_to_mc_db(None)

    with db.sessionmaker() as mc_session:

        snaps = []
        for key, stat in snap_status.items():
            for _key in stat:
                if stat[_key] == "None":
                    stat[_key] = None

            if stat["timestamp"] is None:
                continue

            if stat["serial"] is not None:
                node, loc_num = mc_session._get_node_snap_from_serial(stat["serial"])
            else:
                node, loc_num = None, None
            snap = SnapStatus(
                time=stat["timestamp"],
                hostname=key,
                node=node,
                snap_loc_num=loc_num,
                serial_number=stat["serial"],
                psu_alert=stat["pmb_alert"],
                pps_count=stat["pps_count"],
                fpga_temp=stat["temp"],
                uptime_cycles=stat["uptime"],
                last_programmed_time=stat["last_programmed"],
            )
            snaps.append(snap)
        SnapStatus.objects.bulk_create(snaps, ignore_conflicts=True)
    logger.info("Done")
    return


@periodic_task(
    run_every=(crontab(hour="*/6")), name="get_hookup_notes", ignore_result=True,
)
def update_hookup_notes():
    logger.info("Getting Hookup Notes from M&C")

    db = mc.connect_to_mc_db(None)

    with db.sessionmaker() as mc_session:
        hookup = cm_hookup.Hookup(mc_session)

        hookup_dict = hookup.get_hookup(
            hpn="default",
            pol="all",
            at_date="now",
            exact_match=False,
            use_cache=False,
            hookup_type=None,
        )
        hu_notes = hookup.get_notes(hookup_dict=hookup_dict, state="all")
        notes = []
        for ant_key, ant_notes in hu_notes.items():
            ant_num = int(ant_key.split(":")[0][2:])

            part_hu_hpn = cm_utils.put_keys_in_order(
                list(hu_notes[ant_key].keys()), sort_order="PNR"
            )
            if ant_key in part_hu_hpn:  # Do the hkey first
                part_hu_hpn.remove(ant_key)
                part_hu_hpn = [ant_key] + part_hu_hpn

            for note_key in part_hu_hpn:
                for gtime in hu_notes[ant_key][note_key].keys():
                    time = Time(gtime, format="gps").datetime
                    notes.append(
                        HookupNotes(
                            time=time,
                            ant_number=ant_num,
                            part=note_key,
                            note=hu_notes[ant_key][note_key][gtime],
                        )
                    )

        HookupNotes.objects.bulk_create(notes, ignore_conflicts=True)
    return


@periodic_task(
    run_every=(crontab(minute="*/1")), name="get_ant_status", ignore_result=True,
)
def get_antenna_status_from_redis():
    logger.info("Getting Antenna Status from redis")

    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)
    ant_stats = corr_cm.get_ant_status()
    bulk_add = []
    for antpol, stats in ant_stats.items():
        try:
            antenna = Antenna.objects.get(
                ant_number=int(antpol.split(":")[0]), polarization=antpol.split(":")[1],
            )
        except Antenna.DoesNotExist:
            continue
        for key in stats:
            if stats[key] == "None":
                stats[key] = None

        if stats["fem_id"] is not None and stats["fem_id"] != -1:
            fem_id = _pam_fem_serial_list_to_string(stats["fem_id"])
        else:
            fem_id = None

        if stats["pam_id"] is not None and stats["pam_id"] != -1:
            pam_id = _pam_fem_serial_list_to_string(stats["pam_id"])
        else:
            pam_id = None
        if antenna.polarization == "n":
            fem_lna_power = stats["fem_n_lna_power"]
        elif antenna.polarization == "e":
            fem_lna_power = stats["fem_e_lna_power"]

        antenna_status = AntennaStatus(
            antenna=antenna,
            time=stats["timestamp"],
            snap_hostname=stats["f_host"],
            snap_channel_number=stats["host_ant_id"],
            adc_mean=stats["adc_mean"],
            adc_rms=stats["adc_rms"],
            adc_power=stats["adc_power"],
            pam_atten=stats["pam_atten"],
            pam_power=stats["pam_power"],
            pam_voltage=stats["pam_voltage"],
            pam_current=stats["pam_current"],
            pam_id=pam_id,
            fem_voltage=stats["fem_voltage"],
            fem_current=stats["fem_current"],
            fem_id=fem_id,
            fem_imu=[stats["fem_imu_theta"], stats["fem_imu_phi"]],
            fem_temp=stats["fem_temp"],
            fem_lna_power=fem_lna_power,
            fft_overflow=stats["fft_of"],
            eq_coeffs=stats["eq_coeffs"],
            adc_hist=stats["histogram"],
        )
        bulk_add.append(antenna_status)

    AntennaStatus.objects.bulk_create(bulk_add, ignore_conflicts=True)
    logger.info("Done")
    return
