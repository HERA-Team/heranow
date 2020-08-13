from astropy.time import Time
from argparse import Namespace
from hera_mc import mc, cm_sysutils, cm_utils, cm_sysdef, cm_hookup

from django.core.management.base import BaseCommand, CommandError
from antennas.models import HookupNotes


class Command(BaseCommand):
    help = "Read Hookup notes M&C and update local django database."

    def add_arguments(self, parser):
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
        parser.add_argument(
            "-p",
            "--hpn",
            help="Part number, csv-list or default. (default)",
            default="default",
        )
        parser.add_argument(
            "--hookup-type",
            dest="hookup_type",
            help="Force use of specified hookup type.",
            default=None,
        )

    def handle(self, *args, **options):
        mc_args = Namespace()
        mc_args.mc_db_name = options["mc_db_name"]
        mc_args.mc_config_path = options["mc_config_path"]
        db = mc.connect_to_mc_db(args=mc_args)

        with db.sessionmaker() as mc_session:
            hookup = cm_hookup.Hookup(mc_session)

            hookup_dict = hookup.get_hookup(
                hpn=options["hpn"],
                pol="all",
                at_date="now",
                exact_match=False,
                use_cache=False,
                hookup_type=options["hookup_type"],
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
