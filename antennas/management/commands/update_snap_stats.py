import logging  # noqa
from argparse import Namespace
from hera_corr_cm import HeraCorrCM
from hera_mc import mc

from django.core.management.base import BaseCommand, CommandError
from antennas.models import SnapSpectra, SnapStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Read snapspectra data from redis databse and update local django database."

    def add_arguments(self, parser):
        parser.add_argument("--redishost", default="redishost")
        parser.add_argument("--redisport", default=6379)
        parser.add_argument(
            "--config",
            dest="mc_config_path",
            type=str,
            default=mc.default_config_file,
            help="Path to the mc_config.json configuration file.",
        )
        parser.add_argument(
            "--db",
            dest="mc_db_name",
            type=str,
            help="Name of the database to connect to. The default is used if unspecified.",
        )

    def handle(self, *args, **options):
        corr_cm = HeraCorrCM(redishost=options["redishost"], logger=logger)
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

        snap_status = corr_cm.get_f_status()

        mc_args = Namespace()
        mc_args.mc_db_name = options["mc_db_name"]
        mc_args.mc_config_path = options["mc_config_path"]
        db = mc.connect_to_mc_db(args=mc_args)

        with db.sessionmaker() as mc_session:

            snaps = []
            for key, stat in snap_status.items():
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
