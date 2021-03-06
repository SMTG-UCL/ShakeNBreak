"""
Python test file only to be run locally, when POTCARs are available and the .pmgrc.yaml file is
set up. This cannot be run on GitHub actions as it does not have the POTCARs, preventing POTCAR
and INCAR files from being written.
"""

import unittest
import os
import pickle
import json
import copy
from unittest.mock import patch
import shutil
import warnings

import numpy as np
from matplotlib.testing.compare import compare_images

# Click
from click import exceptions
from click.testing import CliRunner

from pymatgen.core.structure import Structure
from pymatgen.io.vasp.inputs import Incar, Poscar, Kpoints
from doped import vasp_input

from shakenbreak.cli import snb
from shakenbreak import input, io

file_path = os.path.dirname(__file__)


def if_present_rm(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def _update_struct_defect_dict(
    defect_dict: dict, structure: Structure, poscar_comment: str
) -> dict:
    """
    Given a Structure object and POSCAR comment, update the folders dictionary
    (generated with `doped.vasp_input.prepare_vasp_defect_inputs()`) with
    the given values.
    Args:
        defect_dict (:obj:`dict`):
            Dictionary with defect information, as generated with doped
            `prepare_vasp_defect_inputs()`
        structure (:obj:`~pymatgen.core.structure.Structure`):
            Defect structure as a pymatgen object
        poscar_comment (:obj:`str`):
            Comment to include in the top line of the POSCAR file
    Returns:
        single defect dict in the `doped` format.
    """
    defect_dict_copy = copy.deepcopy(defect_dict)
    defect_dict_copy["Defect Structure"] = structure
    defect_dict_copy["POSCAR Comment"] = poscar_comment
    return defect_dict_copy


class DistortionLocalTestCase(unittest.TestCase):
    """Test ShakeNBreak structure distortion helper functions"""

    def setUp(self):
        self.DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
        self.VASP_CDTE_DATA_DIR = os.path.join(self.DATA_DIR, "vasp/CdTe")
        self.EXAMPLE_RESULTS = os.path.join(self.DATA_DIR, "example_results")
        with open(
            os.path.join(self.VASP_CDTE_DATA_DIR, "CdTe_defects_dict.pickle"), "rb"
        ) as fp:
            self.cdte_defect_dict = pickle.load(fp)
        self.V_Cd_dict = self.cdte_defect_dict["vacancies"][0]
        self.Int_Cd_2_dict = self.cdte_defect_dict["interstitials"][1]

        self.V_Cd_struc = Structure.from_file(
            os.path.join(self.VASP_CDTE_DATA_DIR, "CdTe_V_Cd_POSCAR")
        )
        self.V_Cd_minus0pt5_struc_rattled = Structure.from_file(
            os.path.join(
                self.VASP_CDTE_DATA_DIR, "CdTe_V_Cd_-50%_Distortion_Rattled_POSCAR"
            )
        )
        self.V_Cd_minus0pt5_struc_0pt1_rattled = Structure.from_file(
            os.path.join(
                self.VASP_CDTE_DATA_DIR,
                "CdTe_V_Cd_-50%_Distortion_stdev0pt1_Rattled_POSCAR",
            )
        )
        self.V_Cd_minus0pt5_struc_kwarged = Structure.from_file(
            os.path.join(self.VASP_CDTE_DATA_DIR, "CdTe_V_Cd_-50%_Kwarged_POSCAR")
        )
        self.V_Cd_distortion_parameters = {
            "unique_site": np.array([0.0, 0.0, 0.0]),
            "num_distorted_neighbours": 2,
            "distorted_atoms": [(33, "Te"), (42, "Te")],
        }
        self.Int_Cd_2_struc = Structure.from_file(
            os.path.join(self.VASP_CDTE_DATA_DIR, "CdTe_Int_Cd_2_POSCAR")
        )
        self.Int_Cd_2_minus0pt6_struc_rattled = Structure.from_file(
            os.path.join(
                self.VASP_CDTE_DATA_DIR, "CdTe_Int_Cd_2_-60%_Distortion_Rattled_POSCAR"
            )
        )
        self.Int_Cd_2_minus0pt6_NN_10_struc_rattled = Structure.from_file(
            os.path.join(
                self.VASP_CDTE_DATA_DIR, "CdTe_Int_Cd_2_-60%_Distortion_NN_10_POSCAR"
            )
        )
        self.Int_Cd_2_normal_distortion_parameters = {
            "unique_site": self.Int_Cd_2_dict["unique_site"].frac_coords,
            "num_distorted_neighbours": 2,
            "distorted_atoms": [(10, "Cd"), (22, "Cd")],
            "defect_site_index": 65,
        }
        self.Int_Cd_2_NN_10_distortion_parameters = {
            "unique_site": self.Int_Cd_2_dict["unique_site"].frac_coords,
            "num_distorted_neighbours": 10,
            "distorted_atoms": [
                (10, "Cd"),
                (22, "Cd"),
                (29, "Cd"),
                (1, "Cd"),
                (14, "Cd"),
                (24, "Cd"),
                (30, "Cd"),
                (38, "Te"),
                (54, "Te"),
                (62, "Te"),
            ],
            "defect_site_index": 65,
        }

        # Note that Int_Cd_2 has been chosen as a test case, because the first few nonzero bond
        # distances are the interstitial bonds, rather than the bulk bond length, so here we are
        # also testing that the package correctly ignores these and uses the bulk bond length of
        # 2.8333... for d_min in the structure rattling functions.

        self.cdte_defect_folders = [
            "as_1_Cd_on_Te_-1",
            "as_1_Cd_on_Te_-2",
            "as_1_Cd_on_Te_0",
            "as_1_Cd_on_Te_1",
            "as_1_Cd_on_Te_2",
            "as_1_Cd_on_Te_3",
            "as_1_Cd_on_Te_4",
            "as_1_Te_on_Cd_-1",
            "as_1_Te_on_Cd_-2",
            "as_1_Te_on_Cd_0",
            "as_1_Te_on_Cd_1",
            "as_1_Te_on_Cd_2",
            "as_1_Te_on_Cd_3",
            "as_1_Te_on_Cd_4",
            "Int_Cd_1_0",
            "Int_Cd_1_1",
            "Int_Cd_1_2",
            "Int_Cd_2_0",
            "Int_Cd_2_1",
            "Int_Cd_2_2",
            "Int_Cd_3_0",
            "Int_Cd_3_1",
            "Int_Cd_3_2",
            "Int_Te_1_-1",
            "Int_Te_1_-2",
            "Int_Te_1_0",
            "Int_Te_1_1",
            "Int_Te_1_2",
            "Int_Te_1_3",
            "Int_Te_1_4",
            "Int_Te_1_5",
            "Int_Te_1_6",
            "Int_Te_2_-1",
            "Int_Te_2_-2",
            "Int_Te_2_0",
            "Int_Te_2_1",
            "Int_Te_2_2",
            "Int_Te_2_3",
            "Int_Te_2_4",
            "Int_Te_2_5",
            "Int_Te_2_6",
            "Int_Te_3_-1",
            "Int_Te_3_-2",
            "Int_Te_3_0",
            "Int_Te_3_1",
            "Int_Te_3_2",
            "Int_Te_3_3",
            "Int_Te_3_4",
            "Int_Te_3_5",
            "Int_Te_3_6",
            "vac_1_Cd_-1",
            "vac_1_Cd_-2",
            "vac_1_Cd_0",
            "vac_1_Cd_1",
            "vac_1_Cd_2",
            "vac_2_Te_-1",
            "vac_2_Te_-2",
            "vac_2_Te_0",
            "vac_2_Te_1",
            "vac_2_Te_2",
        ]

        self.parsed_default_incar_settings = {
            k: v for k, v in io.default_incar_settings.items() if "#" not in k
        }  # pymatgen doesn't parsed commented lines
        self.parsed_incar_settings_wo_comments = {
            k: v for k, v in self.parsed_default_incar_settings.items() if "#" not in str(v)
        }  # pymatgen ignores comments after values

    def tearDown(self) -> None:
        for i in self.cdte_defect_folders:
            if_present_rm(i)  # remove test-generated vac_1_Cd_0 folder if present
        if os.path.exists("distortion_metadata.json"):
            os.remove("distortion_metadata.json")
        if os.path.exists(f"{os.getcwd()}/distortion_plots"):
            shutil.rmtree(f"{os.getcwd()}/distortion_plots")

    # test create_folder and create_vasp_input simultaneously:
    def test_create_vasp_input(self):
        """Test create_vasp_input function for INCARs and POTCARs"""
        vasp_defect_inputs = vasp_input.prepare_vasp_defect_inputs(
            copy.deepcopy(self.cdte_defect_dict)
        )
        V_Cd_updated_charged_defect_dict = _update_struct_defect_dict(
            vasp_defect_inputs["vac_1_Cd_0"],
            self.V_Cd_minus0pt5_struc_rattled,
            "V_Cd Rattled",
        )
        V_Cd_charged_defect_dict = {
            "Bond_Distortion_-50.0%": V_Cd_updated_charged_defect_dict
        }
        self.assertFalse(os.path.exists("vac_1_Cd_0"))
        input._create_vasp_input(
            "vac_1_Cd_0",
            distorted_defect_dict=V_Cd_charged_defect_dict,
            incar_settings=io.default_incar_settings,
        )
        V_Cd_minus50_folder = "vac_1_Cd_0/Bond_Distortion_-50.0%"
        self.assertTrue(os.path.exists(V_Cd_minus50_folder))
        V_Cd_POSCAR = Poscar.from_file(V_Cd_minus50_folder + "/POSCAR")
        self.assertEqual(V_Cd_POSCAR.comment, "V_Cd Rattled")
        self.assertEqual(V_Cd_POSCAR.structure, self.V_Cd_minus0pt5_struc_rattled)

        V_Cd_INCAR = Incar.from_file(V_Cd_minus50_folder + "/INCAR")
        # check if default INCAR is subset of INCAR:
        self.assertTrue(
            self.parsed_incar_settings_wo_comments.items() <= V_Cd_INCAR.items()
        )

        V_Cd_KPOINTS = Kpoints.from_file(V_Cd_minus50_folder + "/KPOINTS")
        self.assertEqual(V_Cd_KPOINTS.kpts, [[1, 1, 1]])

        # check if POTCARs have been written:
        self.assertTrue(os.path.isfile(V_Cd_minus50_folder + "/POTCAR"))

        # test with kwargs: (except POTCAR settings because we can't have this on the GitHub test
        # server)
        kwarg_incar_settings = {
            "NELECT": 3,
            "IBRION": 42,
            "LVHAR": True,
            "LWAVE": True,
            "LCHARG": True,
            "ENCUT": 200,
        }
        kwarged_incar_settings = self.parsed_incar_settings_wo_comments.copy()
        kwarged_incar_settings.update(kwarg_incar_settings)
        input._create_vasp_input(
            "vac_1_Cd_0",
            distorted_defect_dict=V_Cd_charged_defect_dict,
            incar_settings=kwarged_incar_settings,
        )
        V_Cd_kwarg_minus50_folder = "vac_1_Cd_0/Bond_Distortion_-50.0%"
        self.assertTrue(os.path.exists(V_Cd_kwarg_minus50_folder))
        V_Cd_POSCAR = Poscar.from_file(V_Cd_kwarg_minus50_folder + "/POSCAR")
        self.assertEqual(V_Cd_POSCAR.comment, "V_Cd Rattled")
        self.assertEqual(V_Cd_POSCAR.structure, self.V_Cd_minus0pt5_struc_rattled)

        V_Cd_INCAR = Incar.from_file(V_Cd_kwarg_minus50_folder + "/INCAR")
        # check if default INCAR is subset of INCAR:
        self.assertFalse(
            self.parsed_incar_settings_wo_comments.items() <= V_Cd_INCAR.items()
        )
        self.assertTrue(kwarged_incar_settings.items() <= V_Cd_INCAR.items())

        V_Cd_KPOINTS = Kpoints.from_file(V_Cd_kwarg_minus50_folder + "/KPOINTS")
        self.assertEqual(V_Cd_KPOINTS.kpts, [[1, 1, 1]])

        # check if POTCARs have been written:
        self.assertTrue(os.path.isfile(V_Cd_kwarg_minus50_folder + "/POTCAR"))

    @patch("builtins.print")
    def test_write_vasp_files(self, mock_print):
        """Test write_vasp_files method"""
        oxidation_states = {"Cd": +2, "Te": -2}
        bond_distortions = list(np.arange(-0.6, 0.601, 0.05))

        dist = input.Distortions(
            self.cdte_defect_dict,
            oxidation_states=oxidation_states,
            bond_distortions=bond_distortions,
        )
        distorted_defect_dict, _ = dist.write_vasp_files(
            incar_settings={"ENCUT": 212, "IBRION": 0, "EDIFF": 1e-4},
            verbose=False,
        )

        # check if expected folders were created:
        self.assertTrue(set(self.cdte_defect_folders).issubset(set(os.listdir())))
        # check expected info printing:
        mock_print.assert_any_call(
            "Applying ShakeNBreak...",
            "Will apply the following bond distortions:",
            "['-0.6', '-0.55', '-0.5', '-0.45', '-0.4', '-0.35', '-0.3', "
            "'-0.25', '-0.2', '-0.15', '-0.1', '-0.05', '0.0', '0.05', "
            "'0.1', '0.15', '0.2', '0.25', '0.3', '0.35', '0.4', '0.45', "
            "'0.5', '0.55', '0.6'].",
            "Then, will rattle with a std dev of 0.25 ??? \n",
        )
        mock_print.assert_any_call(
            "\033[1m" + "\nDefect: vac_1_Cd" + "\033[0m"
        )  # bold print
        mock_print.assert_any_call(
            "\033[1m" + "Number of missing electrons in neutral state: 2" + "\033[0m"
        )
        mock_print.assert_any_call(
            "\nDefect vac_1_Cd in charge state: -2. Number of distorted "
            "neighbours: 0"
        )
        mock_print.assert_any_call(
            "\nDefect vac_1_Cd in charge state: -1. Number of distorted "
            "neighbours: 1"
        )
        mock_print.assert_any_call(
            "\nDefect vac_1_Cd in charge state: 0. Number of distorted " "neighbours: 2"
        )
        # test correct distorted neighbours based on oxidation states:
        mock_print.assert_any_call(
            "\nDefect vac_2_Te in charge state: -2. Number of distorted "
            "neighbours: 4"
        )
        mock_print.assert_any_call(
            "\nDefect as_1_Cd_on_Te in charge state: -2. Number of "
            "distorted neighbours: 2"
        )
        mock_print.assert_any_call(
            "\nDefect as_1_Te_on_Cd in charge state: -2. Number of "
            "distorted neighbours: 2"
        )
        mock_print.assert_any_call(
            "\nDefect Int_Cd_1 in charge state: 0. Number of distorted " "neighbours: 2"
        )
        mock_print.assert_any_call(
            "\nDefect Int_Te_1 in charge state: -2. Number of distorted "
            "neighbours: 0"
        )

        # check if correct files were created:
        V_Cd_minus50_folder = "vac_1_Cd_0/Bond_Distortion_-50.0%"
        self.assertTrue(os.path.exists(V_Cd_minus50_folder))
        V_Cd_POSCAR = Poscar.from_file(V_Cd_minus50_folder + "/POSCAR")
        self.assertEqual(
            V_Cd_POSCAR.comment,
            "-50.0%__num_neighbours=2_vac_1_Cd",
        )  # default
        self.assertEqual(V_Cd_POSCAR.structure, self.V_Cd_minus0pt5_struc_rattled)

        V_Cd_INCAR = Incar.from_file(V_Cd_minus50_folder + "/INCAR")
        # check if default INCAR is subset of INCAR: (not here because we set ENCUT)
        self.assertFalse(
            self.parsed_incar_settings_wo_comments.items() <= V_Cd_INCAR.items()
        )
        self.assertEqual(V_Cd_INCAR.pop("ENCUT"), 212)
        self.assertEqual(V_Cd_INCAR.pop("IBRION"), 0)
        self.assertEqual(V_Cd_INCAR.pop("EDIFF"), 1e-4)
        self.assertEqual(V_Cd_INCAR.pop("ROPT"), "1e-3 1e-3")
        parsed_settings = self.parsed_incar_settings_wo_comments.copy()
        parsed_settings.pop("ENCUT")
        self.assertTrue(
            parsed_settings.items() <= V_Cd_INCAR.items()  # matches after
            # removing kwarg settings
        )
        V_Cd_KPOINTS = Kpoints.from_file(V_Cd_minus50_folder + "/KPOINTS")
        self.assertEqual(V_Cd_KPOINTS.kpts, [[1, 1, 1]])

        # check if POTCARs have been written:
        self.assertTrue(os.path.isfile(V_Cd_minus50_folder + "/POTCAR"))

        # Check POSCARs
        Int_Cd_2_minus60_folder = "Int_Cd_2_0/Bond_Distortion_-60.0%"
        self.assertTrue(os.path.exists(Int_Cd_2_minus60_folder))
        Int_Cd_2_POSCAR = Poscar.from_file(Int_Cd_2_minus60_folder + "/POSCAR")
        self.assertEqual(
            Int_Cd_2_POSCAR.comment,
            "-60.0%__num_neighbours=2_Int_Cd_2",
        )
        self.assertEqual(
            Int_Cd_2_POSCAR.structure, self.Int_Cd_2_minus0pt6_struc_rattled
        )

        V_Cd_INCAR = Incar.from_file(V_Cd_minus50_folder + "/INCAR")
        Int_Cd_2_INCAR = Incar.from_file(Int_Cd_2_minus60_folder + "/INCAR")
        # neutral even-electron INCARs the same except for NELECT:
        for incar in [V_Cd_INCAR, Int_Cd_2_INCAR]:
            incar.pop("NELECT")  # https://tenor.com/bgVv9.gif
        self.assertEqual(V_Cd_INCAR, Int_Cd_2_INCAR)
        Int_Cd_2_KPOINTS = Kpoints.from_file(Int_Cd_2_minus60_folder + "/KPOINTS")
        self.assertEqual(Int_Cd_2_KPOINTS.kpts, [[1, 1, 1]])
        # check if POTCARs have been written:
        self.assertTrue(os.path.isfile(Int_Cd_2_minus60_folder + "/POTCAR"))

    def test_plot(self):
        "Test plot() function"
        # Test the following options:
        # --defect, --path, --format,  --units, --colorbar, --metric, --title, --verbose
        defect = "vac_1_Ti_0"
        wd = os.getcwd()  # plots saved to distortion_plots directory in current directory
        with open(f"{self.EXAMPLE_RESULTS}/{defect}/{defect}.txt", "w") as f:
            f.write("")
        runner = CliRunner()
        with warnings.catch_warnings(record=True) as w:
            result = runner.invoke(
                snb,
                [
                    "plot",
                    "-d",
                    defect,
                    "-p",
                    self.EXAMPLE_RESULTS,
                    "--units",
                    "meV",
                    "--format",
                    "png",
                    "--colorbar",
                    "--metric",
                    "disp",
                    "-t", # No title
                    "-v",
                ],
                catch_exceptions=False,
            )
        self.assertTrue(os.path.exists(wd + "/distortion_plots/V$_{Ti}^{0}$.png"))
        compare_images(
            wd + "/distortion_plots/V$_{Ti}^{0}$.png",
            f"{file_path}/remote_baseline_plots/"+"V$_{Ti}^{0}$_cli_colorbar_disp.png",
            tol=2.0,
        )  # only locally (on Github Actions, saved image has a different size)
        self.tearDown()
        [os.remove(os.path.join(self.EXAMPLE_RESULTS, defect, file)) for file in os.listdir(os.path.join(self.EXAMPLE_RESULTS, defect)) if "txt" in file]

        # Test --all option, with the distortion_metadata.json file present to parse number of
        # distorted neighbours and their identities
        defect = "vac_1_Ti_0"
        fake_distortion_metadata = {
            "defects": {
                "vac_1_Cd": {
                    "charges": {
                        "0": {
                            "num_nearest_neighbours": 2,
                            "distorted_atoms": [[33, "Te"], [42, "Te"]]
                        },
                        "-1": {
                            "num_nearest_neighbours": 1,
                            "distorted_atoms": [[33, "Te"],]
                        },
                    }
                },
                "vac_1_Ti": {
                    "charges": {
                        "0": {
                            "num_nearest_neighbours": 3,
                            "distorted_atoms": [[33, "O"], [42, "O"], [40, "O"]]
                        },
                    }
                },
            }
        }
        with open(f"{self.EXAMPLE_RESULTS}/distortion_metadata.json", "w") as f:
            f.write(json.dumps(fake_distortion_metadata, indent=4))
        result = runner.invoke(
            snb,
            [
                "plot",
                "--all",
                "-p",
                self.EXAMPLE_RESULTS,
                "-f",
                "png",
            ],
            catch_exceptions=False,
        )
        self.assertTrue(os.path.exists(wd + "/distortion_plots/V$_{Ti}^{0}$.png"))
        self.assertTrue(os.path.exists(wd + "/distortion_plots/V$_{Cd}^{0}$.png"))
        self.assertTrue(os.path.exists(wd + "/distortion_plots/V$_{Cd}^{-1}$.png"))
        [os.remove(os.path.join(self.EXAMPLE_RESULTS, defect, file)) for file in os.listdir(os.path.join(self.EXAMPLE_RESULTS, defect)) if "txt" in file]
        os.remove(f"{self.EXAMPLE_RESULTS}/distortion_metadata.json")
        # Compare figures
        compare_images(
            wd + "/distortion_plots/V$_{Cd}^{0}$.png",
            f"{file_path}/remote_baseline_plots/"+"V$_{Cd}^{0}$_cli_default.png",
            tol=2.0,
        )  # only locally (on Github Actions, saved image has a different size)
        self.tearDown()

if __name__ == "__main__":
    unittest.main()
