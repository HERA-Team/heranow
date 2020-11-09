"""Initialize antenna objects."""
import os
import logging  # noqa
import numpy as np
from argparse import Namespace
from hera_mc import mc, cm_sysutils

from django.core.management.base import BaseCommand, CommandError
from dashboard.models import Antenna

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command to create antennas in database."""

    help = "Read data from redis databse and update local django database."

    def add_arguments(self, parser):
        """Add additional arguments to command line parser."""
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
        """Perform necessary calculation and inser antennas in to DB."""
        mc_args = Namespace()
        mc_args.mc_db_name = options["mc_db_name"]
        mc_args.mc_config_path = options["mc_config_path"]
        db = mc.connect_to_mc_db(args=mc_args)
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

        Antenna.objects.bulk_create(bulk_add, ignore_conflicts=True)
