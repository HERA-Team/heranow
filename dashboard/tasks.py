import os
import re
import lttb
import redis
import github3
import numpy as np
from astropy.time import Time
from argparse import Namespace
from datetime import datetime, timedelta

from django.utils import timezone

from celery.decorators import task
from celery.utils.log import get_task_logger
from celery.task.schedules import crontab
from celery.decorators import periodic_task

from sqlalchemy import func, and_, or_
from hera_mc import mc, cm_sysutils, cm_utils, cm_sysdef, cm_hookup, cm_partconnect
from hera_mc.correlator import _pam_fem_serial_list_to_string

from hera_corr_cm import HeraCorrCM

from heranow import settings

from dashboard.models import (
    Antenna,
    AntennaStatus,
    AutoSpectra,
    AprioriStatus,
    SnapSpectra,
    SnapStatus,
    HookupNotes,
    CommissioningIssue,
)

logger = get_task_logger(__name__)


@periodic_task(
    run_every=(crontab(minute="*/1")), name="get_autos_from_redis", ignore_result=True,
)
def get_autospectra_from_redis():
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
        timestamp = timezone.make_aware(timestamp.datetime)

        spectra = []
        for antenna in Antenna.objects.all():
            d = rsession.get(f"auto:{antenna.ant_number:d}{antenna.polarization:s}")
            if d is not None:
                auto = np.frombuffer(d, dtype=np.float32)[0:NCHANS].copy()

                downsampled = lttb.downsample(np.stack([freqs, auto,], axis=1), 350,)
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
                    frequencies_downsampled=downsampled[:, 0].tolist(),
                    spectra_downsampled=downsampled[:, 1].tolist(),
                )
                spectra.append(auto_spectra)

        AutoSpectra.objects.bulk_create(spectra, ignore_conflicts=True)
    return


@periodic_task(
    run_every=(crontab(minute="*/1")), name="get_snap_spectra", ignore_result=True,
)
def get_snap_spectra_from_redis():
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)
    snap_spectra = corr_cm.get_snaprf_status()
    spectra_list = []
    for snap_key, stats in snap_spectra.items():
        for key in stats:
            if stats[key] == "None":
                stats[key] = None
            if key == "histogram" and stats[key] is not None:
                if len(stats[key][0]) != len(stats[key][1]):
                    stats[key] = None
        hostname, input_number = snap_key.split(":")
        spectra = SnapSpectra(
            hostname=hostname,
            input_number=input_number,
            time=timezone.make_aware(stats["timestamp"]),
            spectra=stats["autocorrelation"],
            eq_coeffs=stats["eq_coeffs"],
            adc_hist=stats["histogram"],
        )
        spectra_list.append(spectra)

    SnapSpectra.objects.bulk_create(spectra_list, ignore_conflicts=True)
    return


@periodic_task(
    run_every=(crontab(minute="*/1")), name="get_snap_status", ignore_result=True,
)
def get_snap_status_from_redis():
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
                time=timezone.make_aware(stat["timestamp"]),
                hostname=key,
                node=node,
                snap_loc_num=loc_num,
                serial_number=stat["serial"],
                psu_alert=stat["pmb_alert"],
                pps_count=stat["pps_count"],
                fpga_temp=stat["temp"],
                uptime_cycles=stat["uptime"],
                last_programmed_time=timezone.make_aware(stat["last_programmed"]),
            )
            snaps.append(snap)
        SnapStatus.objects.bulk_create(snaps, ignore_conflicts=True)
    return


@periodic_task(
    run_every=(crontab(hour="*/6")), name="get_hookup_notes", ignore_result=True,
)
def update_hookup_notes():
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
            if key == "histogram" and stats[key] is not None:
                if len(stats[key][0]) != len(stats[key][1]):
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
            time=timezone.make_aware(stats["timestamp"]),
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
    return


@periodic_task(
    run_every=(crontab(hour="0", minute="0")),
    name="update_constructed_antenna",
    ignore_result=True,
)
def update_constructed_antennas():
    db = mc.connect_to_mc_db(None)
    antpos = np.genfromtxt(
        os.path.join(mc.data_path, "HERA_350.txt"),
        usecols=(0, 1, 2, 3),
        dtype={
            "names": ("ANTNAME", "EAST", "NORTH", "UP"),
            "formats": ("<U5", "<f8", "<f8", "<f8"),
        },
        encoding=None,
    )
    antnames = antpos["ANTNAME"]
    inds = [int(j[2:]) for j in antnames]
    inds = np.argsort(inds)

    antnames = np.take(antnames, inds)

    antpos = np.array([antpos["EAST"], antpos["NORTH"], antpos["UP"]])
    array_center = np.mean(antpos, axis=1, keepdims=True)
    antpos -= array_center
    antpos = np.take(antpos, inds, axis=1)

    with db.sessionmaker() as session:
        hsession = cm_sysutils.Handling(session)

        stations = []
        for station_type in hsession.geo.parse_station_types_to_check("default"):
            for stn in hsession.geo.station_types[station_type]["Stations"]:
                stations.append(stn)

        # stations is a list of HH??? numbers we just want the ints
        stations = list(map(int, [j[2:] for j in stations]))

        bulk_add = []
        for ind, name in enumerate(antnames):
            ant_number = int(name[2:])
            for pol in ["e", "n"]:
                bulk_add.append(
                    Antenna(
                        ant_number=ant_number,
                        ant_name=name,
                        polarization=pol,
                        antpos_enu=antpos[:, ind].tolist(),
                        constructed=ant_number in stations,
                    )
                )

    Antenna.objects.bulk_update(bulk_add, ["constructed"])


def get_mc_apriori(handling, antenna):
    if isinstance(antenna, Antenna):
        ant = antenna.ant_name.upper()
    else:
        ant = antenna.upper()
    at_date = Time.now().gps
    cmapa = cm_partconnect.AprioriAntenna
    apa = (
        handling.session.query(cmapa)
        .filter(
            or_(
                and_(
                    func.upper(cmapa.antenna) == ant,
                    cmapa.start_gpstime <= at_date,
                    cmapa.stop_gpstime.is_(None),
                ),
                and_(
                    func.upper(cmapa.antenna) == ant,
                    cmapa.start_gpstime <= at_date,
                    cmapa.stop_gpstime > at_date,
                ),
            )
        )
        .first()
    )
    return apa


@periodic_task(
    run_every=(crontab(hour="*/1", minute="0")),
    name="update_apriori",
    ignore_result=True,
)
def update_apriori():
    db = mc.connect_to_mc_db(None)

    with db.sessionmaker() as session:
        handling = cm_sysutils.Handling(session)
        pol_list = [
            p["polarization"]
            for p in Antenna.objects.order_by().values("polarization").distinct()
        ]
        a_stats = []
        for names in (
            Antenna.objects.filter(constructed=True)
            .order_by()
            .values("ant_name")
            .distinct()
        ):
            ant_name = names["ant_name"]
            status = get_mc_apriori(handling, ant_name)
            if status is not None and status.status != "not_connected":
                for ant in Antenna.objects.filter(
                    ant_name=ant_name, polarization__in=pol_list
                ):
                    if status.status not in AprioriStatus._mc_apriori_mapping.keys():
                        # some antennas still have old mappings, just ignore for now
                        continue
                    a_stats.append(
                        AprioriStatus(
                            antenna=ant,
                            time=timezone.make_aware(
                                Time(status.start_gpstime, format="gps").datetime
                            ),
                            apriori_status=AprioriStatus._mc_apriori_mapping[
                                status.status
                            ],
                        )
                    )
        AprioriStatus.objects.bulk_create(a_stats, ignore_conflicts=True)
    return


@periodic_task(
    run_every=(crontab(hour="*/6")), name="update_issue_log", ignore_result=True,
)
def update_issue_log():
    key = settings.GITHUB_APP_KEY
    app_id = settings.GITHUB_APP_ID

    gh = github3.github.GitHub()
    gh.login_as_app(key.encode(), app_id)
    ap = gh.authenticated_app()
    inst = gh.app_installation_for_repository("HERA-Team", "HERA_Commissioning")
    gh.login_as_app_installation(key.encode(), ap.id, inst.id)
    repo = gh.repository("HERA-Team", "HERA_Commissioning")

    issues = repo.issues(labels="Daily", state="all")

    local_issue_regex = r"[^a-zA-Z0-9]#(\d+)"
    # the foreign issue reference may be useful in the future
    # foreign_issue_regex = r"[a-zA-Z0-9]#(\d+)"

    for issue in issues:
        # only look at issues edited in the last 6 hours
        if not issue.updated_at >= timezone.make_aware(datetime.now()) - timedelta(
            hours=6
        ):
            continue

        try:
            jd = int(issue.title.split(" ")[-1])
        except ValueError:
            match = re.search(r"\d{7}", issue.title)
            if match is not None:
                jd = int(match.group())
            else:
                continue

        obs_date = Time(jd, format="jd")

        obs_date = timezone.make_aware(obs_date.datetime)
        obs_end = obs_date + timedelta(days=1)

        num_opened = len(
            list(repo.issues(state="all", sort="created", since=obs_date))
        ) - len(list(repo.issues(state="all", sort="created", since=obs_end)))

        other_labels = [lab.name for lab in issue.labels() if lab.name != "Daily"]
        iss_nums = map(int, re.findall(local_issue_regex, issue.body))
        related_issues = set()
        related_issues.update(iss_nums)
        for comm in issue.comments():
            nums = map(int, re.findall(local_issue_regex, issue.body))
            related_issues.update(nums)
        related_issues = sorted(related_issues)

        iss_values = dict(
            julian_date=jd,
            number=issue.number,
            related_issues=related_issues,
            labels=other_labels,
            new_issues=num_opened,
        )

        CommissioningIssue.objects.update_or_create(julian_date=jd, defaults=iss_values)

    # check if the current JD exists, otherwise create it
    current_jd = np.floor(Time.Now().jd)
    CommissioningIssue.objects.update_or_create(julian_date=current_jd)
    return
