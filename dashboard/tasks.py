"""Definition of tasks performed by celery to keep database up to date."""
import os
import re
import json
import lttb
import redis
import healpy
import github3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from argparse import Namespace
from pyuvdata import get_telescope
from datetime import datetime, timedelta

from astropy.time import Time
from astropy import coordinates

from django.utils import timezone

from celery import shared_task
from celery.utils.log import get_task_logger

from sqlalchemy import func, and_, or_
from hera_mc.correlator import _pam_fem_id_to_string
from hera_mc import mc, cm_sysutils, cm_utils, cm_sysdef, cm_hookup, cm_partconnect

from hera_corr_cm import HeraCorrCM

from heranow import settings

from dashboard.models import (
    Antenna,
    AntennaStatus,
    AntToSnap,
    AprioriStatus,
    AutoSpectra,
    CommissioningIssue,
    HookupNotes,
    SnapSpectra,
    SnapStatus,
    SnapToAnt,
    XengChannels,
)

logger = get_task_logger(__name__)


@shared_task
def get_autospectra_from_redis():
    """Get autospectra from redis and add new correlations to database."""
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
        print(f"AUTOSPECTRA last timestamp: {timestamp}")

        spectra = []
        for antenna in Antenna.objects.all():
            d = rsession.get(f"auto:{antenna.ant_number:d}{antenna.polarization:s}")
            if d is not None:
                auto = np.frombuffer(d, dtype=np.float32)[0:NCHANS].copy()

                downsampled = lttb.downsample(np.stack([freqs, auto,], axis=1), 350,)
                eq_coeffs = rsession.hget(
                    f"eq:ant:{antenna.ant_number:d}:{antenna.polarization:s}", "values",
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


@shared_task
def get_snap_spectra_from_redis():
    """Get snap spectra from redis and add to database."""
    bins = np.arange(-128, 127)
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)
    snap_spectra = corr_cm.get_snaprf_status()
    spectra_list = []
    for snap_key, stats in snap_spectra.items():
        for key in stats:
            if stats[key] == "None":
                stats[key] = None
            if key == "histogram" and stats[key] is not None:
                if np.size(stats[key]) == 255:
                    stats[key] = np.asarray([bins, stats["histogram"]]).tolist()
                elif np.shape(stats[key]) == 2 and len(stats[key][0]) != len(
                    stats[key][1]
                ):
                    stats[key] = None
        hostname, input_number = snap_key.split(":")
        try:
            spectra = SnapSpectra(
                hostname=hostname,
                input_number=input_number,
                time=timezone.make_aware(stats["timestamp"]),
                spectra=stats["autocorrelation"],
                eq_coeffs=stats["eq_coeffs"],
                adc_hist=stats["histogram"],
            )
        except:  # noqa
            print(f"Error processing Snap {snap_key}")
            continue
        spectra_list.append(spectra)

    SnapSpectra.objects.bulk_create(spectra_list, ignore_conflicts=True)
    return


@shared_task
def get_snap_status_from_redis():
    """Get snap status from redis and add to database."""
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)

    snap_status = corr_cm.get_f_status()

    db = mc.connect_to_mc_db(None)

    with db.sessionmaker() as mc_session:

        snaps = []
        for key, stat in snap_status.items():

            try:
                for _key in stat:
                    if stat[_key] == "None":
                        stat[_key] = None

                if stat["timestamp"] is None:
                    continue

                if stat["serial"] is not None:
                    node, loc_num = mc_session._get_node_snap_from_serial(
                        stat["serial"]
                    )
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
            except Exception as err:
                print(f"Error with snap {key}. {err}")
                continue

            snaps.append(snap)
        SnapStatus.objects.bulk_create(snaps, ignore_conflicts=True)
    return


@shared_task
def update_hookup_notes():
    """Read hookup notes from M&C and add new notes to database."""
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
        hu_notes = hookup.get_notes(
            hookup_dict=hookup_dict, state="all", return_dict=True
        )
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
                            time=timezone.make_aware(time),
                            ant_number=ant_num,
                            part=note_key,
                            note=hu_notes[ant_key][note_key][gtime]["note"],
                            reference=hu_notes[ant_key][note_key][gtime]["ref"],
                        )
                    )

        HookupNotes.objects.bulk_create(notes, ignore_conflicts=True)
    return


@shared_task
def get_antenna_status_from_redis():
    """Get antenna status from redis and add new statuses to database."""
    bins = np.arange(-128, 127)
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
        try:
            for key in stats:
                if stats[key] == "None":
                    stats[key] = None
                if key == "histogram" and stats[key] is not None:
                    if np.size(stats[key]) == 255:
                        stats[key] = np.asarray([bins, stats["histogram"]]).tolist()
                    elif np.shape(stats[key]) == 2 and len(stats[key][0]) != len(
                        stats[key][1]
                    ):
                        stats[key] = None
                if key == "fem_switch" and (
                    stats[key] == "null" or stats[key] == "Unknown mode"
                ):
                    stats[key] = None

            if stats["fem_id"] is not None and stats["fem_id"] != -1:
                fem_id = _pam_fem_id_to_string(stats["fem_id"])
            else:
                fem_id = None

            if stats["fem_switch"] is None:
                fem_switch = None
            else:
                fem_switch = AntennaStatus._fem_mapping[stats["fem_switch"].lower()]

            if stats["pam_id"] is not None and stats["pam_id"] != -1:
                pam_id = _pam_fem_id_to_string(stats["pam_id"])
            else:
                pam_id = None

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
                fem_lna_power=stats["fem_lna_power"],
                fem_switch=fem_switch,
                fft_overflow=stats["fft_of"],
                eq_coeffs=stats["eq_coeffs"],
                adc_hist=stats["histogram"],
            )
        except Exception as e:  # noqa
            print(f"Error processing Antenna {antpol}. {e}")
            continue
        bulk_add.append(antenna_status)

    AntennaStatus.objects.bulk_create(bulk_add, ignore_conflicts=True)
    return


@shared_task
def update_constructed_antennas():
    """Check antennas marked as constructed and update database."""
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
                ant = Antenna.objects.get(
                    ant_number=ant_number,
                    ant_name=name,
                    polarization=pol,
                    antpos_enu=antpos[:, ind].tolist(),
                )
                ant.constructed = ant_number in stations
                bulk_add.append(ant)

    Antenna.objects.bulk_update(bulk_add, ["constructed"])


def get_mc_apriori(handling, antenna):
    """Query M&C database for apriori status.

    Parameters
    ----------
    handling : M&C cm_sysutils Handling object
        Object which performs query to M&C database
    antenna : Antenna Object
        Antenna to get status for.

    """
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


@shared_task
def update_apriori():
    """Get most recent Apriori status for each Antenna and update database."""
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


@shared_task
def update_issue_log():
    """Query Github for all Daily Log issues updated in the last 6 hours."""
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
    current_jd = np.floor(Time.now().jd)
    CommissioningIssue.objects.update_or_create(julian_date=current_jd)
    return


@shared_task
def replot_radiosky():
    """Calculate current sidereal time and plot sky over HERA."""
    radio_map = healpy.read_map(os.path.join(settings.BASE_DIR, "test4.fits"))
    hera_telescope = get_telescope("HERA")
    hera_loc = coordinates.EarthLocation.from_geocentric(
        *hera_telescope.telescope_location, unit="m",
    )
    hera_time = Time.now()
    hera_time.location = hera_loc
    sidereal_time = hera_time.sidereal_time("apparent")

    healpy_rotation = [
        sidereal_time.to_value("deg") - 360,
        hera_loc.geodetic.lat.to_value("deg"),
    ]

    moon = coordinates.get_moon(hera_time, ephemeris=None)
    sun = coordinates.get_sun(hera_time)

    pic = coordinates.SkyCoord(ra="05h19m49.7230919028", dec="-45d 46m 44s")  # Pictor
    forn = coordinates.SkyCoord(ra="03h23m25.1s", dec="-37d 08m")
    cass = coordinates.SkyCoord(ra="23h 23m 24s", dec="+58d 48.9m")
    crab = coordinates.SkyCoord(ra="05h 34m 31s", dec="+22d 00m 52.2s")
    lmc = coordinates.SkyCoord(ra="05h 40m 05s", dec="-69d 45m 51s")
    smc = coordinates.SkyCoord(ra="00h 52m 44.8s", dec="-72d 49m 43s")
    cenA = coordinates.SkyCoord(ra="13h 25m 27.6s", dec="-43d 01m 09s")
    callibrator1 = coordinates.SkyCoord(ra=109.32351, dec=-25.0817, unit="deg",)
    callibrator2 = coordinates.SkyCoord(ra=30.05044, dec=-30.89106, unit="deg")
    callibrator3 = coordinates.SkyCoord(ra=6.45484, dec=-26.0363, unit="deg",)

    source_list = [
        {"source": sun, "name": "sun", "color": "y", "size": 1000},
        {"source": moon, "name": "moon", "color": "slategrey", "size": 200},
        {"source": pic, "name": "pictor", "color": "w", "size": 50},
        {"source": forn, "name": "fornax", "color": "w", "size": 50},
        {"source": cass, "name": "Cass A", "color": "w", "size": 50},
        {"source": crab, "name": "Crab", "color": "w", "size": 50},
        {"source": lmc, "name": "LMC", "color": "w", "size": 50},
        {"source": cenA, "name": "Cen A", "color": "w", "size": 50},
        {"source": smc, "name": "SMC", "color": "w", "size": 50},
        {"source": callibrator1, "name": "J071717.6-250454", "color": "r", "size": 50},
        {"source": callibrator2, "name": "J020012.1-305327", "color": "r", "size": 50},
        {"source": callibrator3, "name": "J002549.1-260210", "color": "r", "size": 50},
    ]

    healpy.orthview(
        np.log10(radio_map),
        title=sidereal_time.to_string(),
        coord=["G", "C"],
        rot=healpy_rotation,
        return_projected_map=True,
        min=0,
        max=2,
        half_sky=1,
    )

    for item in source_list:
        sky_loc = item["source"]
        healpy.projscatter(
            sky_loc.ra,
            sky_loc.dec,
            lonlat=True,
            s=item["size"],
            c=item["color"],
            label=item["name"],
        )
        healpy.projtext(sky_loc.ra, sky_loc.dec, lonlat=True, color="k", s=item["name"])

    solar_bodies = [
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "neptune",
        "uranus",
    ]
    colors = ["grey", "pink", "red", "orange", "yellow", "blue", "blue", "blue"]

    for name, color in zip(solar_bodies, colors):
        body = coordinates.get_body(name, hera_time)
        healpy.projscatter(
            body.ra, body.dec, lonlat=True, s=50, color=color, label=name
        )
        healpy.projtext(body.ra, body.dec, lonlat=True, color="k", s=name)

    filename = settings.MEDIA_ROOT / "radiosky.png"
    plt.savefig(
        filename, bbox_inches="tight", pad_inches=0.2,
    )
    return


@shared_task
def update_hookup():
    """Get most recent hookup notes from M&C."""
    db = mc.connect_to_mc_db(None)

    with db.sessionmaker() as mc_session:

        H = cm_hookup.Hookup(mc_session)
        hlist = cm_sysdef.hera_zone_prefixes
        output_file = settings.BASE_DIR / "templates" / "sys_conn_tmp.html"

        hookup_dict = H.get_hookup(
            hpn=hlist, pol="all", at_date="now", exact_match=False, hookup_type=None,
        )
        H.show_hookup(
            hookup_dict=hookup_dict,
            cols_to_show="all",
            state="full",
            ports=True,
            revs=True,
            sortby="node,station",
            filename=output_file,
            output_format="html",
        )


@shared_task
def update_xengs():
    """Grab Xeng configuration from redis."""
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)
    xeng_chan_mapping = corr_cm.r.hgetall("corr:xeng_chans")
    bulk_objects = []
    xeng_time = timezone.make_aware(datetime.now())
    for xeng, chans in xeng_chan_mapping.items():
        xeng = int(xeng)
        chans = json.loads(chans)
        bulk_objects.append(XengChannels(time=xeng_time, number=xeng, chans=chans,))
    XengChannels.objects.bulk_create(bulk_objects, ignore_conflicts=True)
    return


@shared_task
def update_ant_to_snap():
    """Get ant to snap mapping from redis."""
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)
    corr_map = corr_cm.r.hgetall("corr:map")

    update_time = Time(float(corr_map["update_time"]), format="unix").datetime

    ant_to_snap = json.loads(corr_map["ant_to_snap"])
    bulk_objects = []
    for ant in sorted(map(int, ant_to_snap)):
        ant = str(ant)
        pol = ant_to_snap[ant]
        for p in pol:
            vals = pol[p]
            host = vals["host"]
            chan = vals["channel"]
            antenna = Antenna.objects.get(ant_number=ant, polarization=p)
            bulk_objects.append(
                AntToSnap(
                    time=timezone.make_aware(update_time),
                    antenna=antenna,
                    snap_hostname=host,
                    chan=chan,
                )
            )
    AntToSnap.objects.bulk_create(bulk_objects, ignore_conflicts=True)
    return


@shared_task
def update_snap_to_ant():
    """Get snap to ant mapping from redis."""
    corr_cm = HeraCorrCM(redishost="redishost", logger=logger)
    corr_map = corr_cm.r.hgetall("corr:map")

    update_time = Time(float(corr_map["update_time"]), format="unix").datetime

    snap_to_ant = json.loads(corr_map["snap_to_ant"])
    snap_to_ant_inds = corr_cm.r.hgetall("corr:snap_ants")
    bulk_objects = []
    for host in sorted(snap_to_ant):
        ants = [a or "N/A" for a in snap_to_ant[host]]
        try:
            ant_inds = json.loads(snap_to_ant_inds[host])
        except KeyError:
            ant_inds = None

        match = re.search(r"heraNode(?P<node>\d+)Snap(?P<snap>\d+)", host)
        if match is not None:
            node = int(match.group("node"))
            snap = int(match.group("snap"))
        else:
            node = None
            snap = None

        bulk_objects.append(
            SnapToAnt(
                time=timezone.make_aware(update_time),
                snap_hostname=host,
                node=node,
                snap=snap,
                ants=ants,
                inds=ant_inds,
            )
        )

    SnapToAnt.objects.bulk_create(bulk_objects, ignore_conflicts=True)
    return


@shared_task
def antenna_stats_to_csv():
    """Turn antenna stats to csv for hera lights board."""
    df = []

    # a shorter variable to help with the text section
    last_spectra = AutoSpectra.objects.last()
    if last_spectra is not None:
        all_spectra = AutoSpectra.objects.filter(time=last_spectra.time)
    else:
        all_spectra = None

    for antenna in Antenna.objects.all():
        data = {
            "ant": antenna.ant_number,
            "pol": f"{antenna.polarization}",
            "constructed": antenna.constructed,
            "node": "Unknown",
            "fem_switch": "Unknown",
            "apriori": "Unknown",
        }
        stat = AntennaStatus.objects.filter(antenna=antenna).order_by("time").last()
        if stat is None:
            if antenna.constructed:
                # They are actually constructed but with no status they are OFFLINE
                # a little hacky way to get it to display properly out of the DataFrame
                data["constructed"] = False

        else:
            node = "Unknown"
            match = re.search(r"heraNode(?P<node>\d+)Snap", stat.snap_hostname)
            if match is not None:
                node = int(match.group("node"))

            apriori = "Unknown"
            apriori_stat = (
                AprioriStatus.objects.filter(antenna=stat.antenna)
                .order_by("time")
                .last()
            )
            if apriori_stat is not None:
                apriori = apriori_stat.get_apriori_status_display()
            if all_spectra is not None:
                try:
                    auto = all_spectra.get(antenna=antenna)
                except AutoSpectra.DoesNotExist:
                    auto = None
                if auto is not None:

                    if auto.eq_coeffs is not None:
                        spectra = (
                            np.array(auto.spectra) / np.median(auto.eq_coeffs) ** 2
                        )
                    else:
                        spectra = auto.spectra
                    spectra = (
                        (10 * np.log10(np.ma.masked_invalid(spectra)))
                        .filled(-100)
                        .mean()
                    )
                else:
                    spectra = None
            else:
                spectra = None

            adc_power = (
                10 * np.log10(stat.adc_power) if stat.adc_power is not None else None
            )
            data.update(
                {
                    "spectra": spectra,
                    "node": node,
                    "apriori": apriori,
                    "pam_power": stat.pam_power,
                    "adc_power": adc_power,
                    "adc_rms": stat.adc_rms,
                    "fem_imu_theta": stat.fem_imu[0],
                    "fem_imu_phi": stat.fem_imu[1],
                    "eq_coeffs": np.median(stat.eq_coeffs)
                    if stat.eq_coeffs is not None
                    else None,
                    "fem_switch": stat.get_fem_switch_display(),
                }
            )

        df.append(data)

    df = pd.DataFrame(df)

    # Sort according to increasing antpols
    if not df.empty:
        df.sort_values(["ant", "pol"], inplace=True)
        df.reset_index(inplace=True, drop=True)

    filename = settings.MEDIA_ROOT / "ant_stats.csv"
    with open(filename, "w") as outfile:
        df.to_csv(outfile, index=False)

    return


@shared_task
def delete_old_data():
    """Remove data from bigger models older than a month."""
    for model in [AutoSpectra, AntennaStatus, SnapStatus, SnapSpectra]:
        # get everything older than the timeframe,
        # don't delete if it is the latest one though
        pass
