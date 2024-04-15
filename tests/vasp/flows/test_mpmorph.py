"""Test MPMorph VASP flows."""

import pytest

from atomate2.common.flows.mpmorph import EquilibriumVolumeMaker, MPMorphMDMaker
from atomate2.vasp.jobs.md import MDMaker
from atomate2.vasp.sets.core import MDSetGenerator
from atomate2.vasp.run import _DEFAULT_HANDLERS
from pymatgen.io.vasp import Kpoints
from jobflow import run_locally

from pymatgen.core import Structure


def test_equilibrium_volume_maker(mock_vasp, clean_dir, vasp_test_dir):

    ref_paths = {
        "Equilibrium Volume Maker molecular dynamics 1": "Si_mp_morph/Si_0.8",
        "Equilibrium Volume Maker molecular dynamics 2": "Si_mp_morph/Si_1.0",
        "Equilibrium Volume Maker molecular dynamics 3": "Si_mp_morph/Si_1.2",
    }

    mock_vasp(ref_paths)

    intial_structure = Structure.from_file(
        f"{vasp_test_dir}/Si_mp_morph/Si_1.0/inputs/POSCAR.gz"
    )
    temperature: int = 300
    end_temp: int = 300
    steps_convergence: int = 20

    gamma_point = Kpoints(
        comment="Gamma only",
        num_kpts=1,
        kpts=[[0, 0, 0]],
        kpts_weights=[1.0],
    )
    incar_settings = {
        "ISPIN": 1,  # Do not consider magnetism in AIMD simulations
        "LREAL": "Auto",  # Peform calculation in real space for AIMD due to large unit cell size
        "LAECHG": False,  # Don't need AECCAR for AIMD
        "EDIFFG": None,  # Does not apply to MD simulations, see: https://www.vasp.at/wiki/index.php/EDIFFG
        "GGA": "PS",  # Just let VASP decide based on POTCAR - the default, PS yields the error below
        "LPLANE": False,  # LPLANE is recommended to be False on Cray machines (https://www.vasp.at/wiki/index.php/LPLANE)
        "LDAUPRINT": 0,
    }

    aimd_equil_maker = MDMaker(
        input_set_generator=MDSetGenerator(
            ensemble="nvt",
            start_temp=temperature,
            end_temp=end_temp,
            nsteps=steps_convergence,
            time_step=2,
            # adapted from MPMorph settings
            user_incar_settings=incar_settings,
            user_kpoints_settings=gamma_point,
        )
    )

    flow = EquilibriumVolumeMaker(
        md_maker=aimd_equil_maker,
    ).make(structure=intial_structure)

    responses = run_locally(flow, create_folders=True, ensure_success=True)

    ref_md_energies = {
        "energy": [-13.44200043, -35.97470303, -32.48531985],
        "volume": [82.59487098351644, 161.31810738968053, 278.7576895693679],
    }
    uuids = [uuid for uuid in responses]
    # print([responses[uuid][1].output for uuid in responses])
    # print("-----STARTING PRINT-----")
    # print([uuid for uuid in responses])
    # print(responses[uuids[0]][1].output)
    # print("-----ENDING PRINT-----")
    # asserting False so that stdout is printed by pytest

    assert len(uuids) == 5
    for i in range(len(ref_md_energies["energy"])):
        assert responses[uuids[1 + i]][
            1
        ].output.output.structure.volume == pytest.approx(ref_md_energies["volume"][i])
        assert responses[uuids[1 + i]][1].output.output.energy == pytest.approx(
            ref_md_energies["energy"][i]
        )

    assert isinstance(responses[uuids[4]][1].output, Structure)
    assert responses[uuids[4]][1].output.volume == pytest.approx(171.51227)

    """
    assert responses[uuids[0]][1].output == {
        "relax": {
            "energy": [-13.44200043, -35.97470303, -32.48531985],
            "volume": [82.59487098351644, 161.31810738968053, 278.7576895693679],
            "stress": [
                [
                    [2026.77697447, -180.19246839, -207.37762676],
                    [-180.1924744, 1441.18625768, 27.8884401],
                    [-207.37763076, 27.8884403, 1899.32511191],
                ],
                [
                    [36.98140157, 35.7070696, 76.84918574],
                    [35.70706985, 42.81953297, -25.20830843],
                    [76.84918627, -25.20830828, 10.40947728],
                ],
                [
                    [-71.39703139, -5.93838689, -5.13934938],
                    [-5.93838689, -72.87372166, -3.0206588],
                    [-5.13934928, -3.0206586, -57.65692738],
                ],
            ],
            "pressure": [1789.0961146866666, 30.070137273333334, -67.30922681],
            "EOS": {
                "b0": 424.97840444799994,
                "b1": 4.686114896027117,
                "v0": 171.51226566279973,
            },
        },
        "V0": 171.51226566279973,
        "Vmax": 278.7576895693679,
        "Vmin": 82.59487098351644,
    }
    """


def test_recursion_equilibrium_volume_maker(mock_vasp, clean_dir, vasp_test_dir):

    ref_paths = {
        "Equilibrium Volume Maker molecular dynamics 1": "Si_mp_morph/recursion/Si_3.48",
        "Equilibrium Volume Maker molecular dynamics 2": "Si_mp_morph/recursion/Si_4.35",
        "Equilibrium Volume Maker molecular dynamics 3": "Si_mp_morph/recursion/Si_5.22",
        "Equilibrium Volume Maker molecular dynamics 4": "Si_mp_morph/recursion/Si_6.80",
    }

    mock_vasp(ref_paths)

    intial_structure = Structure.from_file(
        f"{vasp_test_dir}/Si_mp_morph/recursion/Si_4.35/inputs/POSCAR.gz"
    )
    temperature: int = 300
    end_temp: int = 300
    steps_convergence: int = 20

    gamma_point = Kpoints(
        comment="Gamma only",
        num_kpts=1,
        kpts=[[0, 0, 0]],
        kpts_weights=[1.0],
    )
    incar_settings = {
        "ISPIN": 1,  # Do not consider magnetism in AIMD simulations
        "LREAL": "Auto",  # Peform calculation in real space for AIMD due to large unit cell size
        "LAECHG": False,  # Don't need AECCAR for AIMD
        "EDIFFG": None,  # Does not apply to MD simulations, see: https://www.vasp.at/wiki/index.php/EDIFFG
        "GGA": "PS",  # Just let VASP decide based on POTCAR - the default, PS yields the error below
        "LPLANE": False,  # LPLANE is recommended to be False on Cray machines (https://www.vasp.at/wiki/index.php/LPLANE)
        "LDAUPRINT": 0,
    }

    # For close separations, positive energy is reasonable and expected
    _vasp_handlers = [
        handler for handler in _DEFAULT_HANDLERS if "PositiveEnergy" not in str(handler)
    ]

    aimd_equil_maker = MDMaker(
        input_set_generator=MDSetGenerator(
            ensemble="nvt",
            start_temp=temperature,
            end_temp=end_temp,
            nsteps=steps_convergence,
            time_step=2,
            # adapted from MPMorph settings
            user_incar_settings=incar_settings,
            user_kpoints_settings=gamma_point,
        ),
        run_vasp_kwargs={"handlers": _vasp_handlers},
    )

    flow = EquilibriumVolumeMaker(
        md_maker=aimd_equil_maker,
    ).make(structure=intial_structure)

    responses = run_locally(flow, create_folders=True, ensure_success=True)

    pre_recursion_ref_md_energies = {
        "energy": [71.53406556, -14.64974676, -35.39207478],
        "volume": [42.28857394356042, 82.59487098351644, 142.7239370595164],
        "V0": 170.97868797782795,
        "Vmax": 142.7239370595164,
        "Vmin": 42.28857394356042,
    }

    post_recursion_ref_md_energies = {
        "energy": [71.53406556, -14.64974676, -35.39207478, -31.18239194],
        "volume": [
            42.28857394356042,
            82.59487098351644,
            142.7239370595164,
            314.80734557888934,
        ],
        "V0": 170.97868797782795,
        "Vmax": 142.7239370595164,  # this needs to be updated...
        "Vmin": 42.28857394356042,
    }

    uuids = [uuid for uuid in responses]

    # print("-----STARTING PRINT-----")
    # print([uuid for uuid in responses])
    # print(uuids)
    # print("sixth job", [responses[uuids[5]][1].output]) #recursion job
    # print("-----ENDING PRINT-----")

    # asserting False so that stdout is printed by pytest
    assert len(uuids) == 7

    for i in range(len(pre_recursion_ref_md_energies["energy"])):
        assert responses[uuids[1 + i]][
            1
        ].output.output.structure.volume == pytest.approx(
            pre_recursion_ref_md_energies["volume"][i]
        )
        assert responses[uuids[1 + i]][1].output.output.energy == pytest.approx(
            pre_recursion_ref_md_energies["energy"][i]
        )

    assert responses[uuids[5]][1].output.output.structure.volume == pytest.approx(
        post_recursion_ref_md_energies["volume"][3]
    )
    assert responses[uuids[5]][1].output.output.energy == pytest.approx(
        post_recursion_ref_md_energies["energy"][3]
    )

    assert isinstance(responses[uuids[-1]][1].output, Structure)
    assert responses[uuids[-1]][1].output.volume == pytest.approx(177.244197)


def test_mp_morph_maker(mock_vasp, clean_dir, vasp_test_dir):

    ref_paths = {
        "Equilibrium Volume Maker molecular dynamics 1": "Si_mp_morph/Si_0.8",
        "Equilibrium Volume Maker molecular dynamics 2": "Si_mp_morph/Si_1.0",
        "Equilibrium Volume Maker molecular dynamics 3": "Si_mp_morph/Si_1.2",
        "MP Morph md production run": "Si_mp_morph/Si_prod",
    }

    mock_vasp(ref_paths)

    intial_structure = Structure.from_file(
        f"{vasp_test_dir}/Si_mp_morph/Si_1.0/inputs/POSCAR.gz"
    )
    temperature: int = 300
    end_temp: int = 300
    steps_convergence: int = 20
    steps_production: int = 50

    gamma_point = Kpoints(
        comment="Gamma only",
        num_kpts=1,
        kpts=[[0, 0, 0]],
        kpts_weights=[1.0],
    )
    incar_settings = {
        "ISPIN": 1,  # Do not consider magnetism in AIMD simulations
        "LREAL": "Auto",  # Peform calculation in real space for AIMD due to large unit cell size
        "LAECHG": False,  # Don't need AECCAR for AIMD
        "EDIFFG": None,  # Does not apply to MD simulations, see: https://www.vasp.at/wiki/index.php/EDIFFG
        "GGA": "PS",  # Just let VASP decide based on POTCAR - the default, PS yields the error below
        "LPLANE": False,  # LPLANE is recommended to be False on Cray machines (https://www.vasp.at/wiki/index.php/LPLANE)
        "LDAUPRINT": 0,
    }

    aimd_equil_maker = MDMaker(
        input_set_generator=MDSetGenerator(
            ensemble="nvt",
            start_temp=temperature,
            end_temp=end_temp,
            nsteps=steps_convergence,
            time_step=2,
            # adapted from MPMorph settings
            user_incar_settings=incar_settings,
            user_kpoints_settings=gamma_point,
        )
    )

    aimd_prod_maker = MDMaker(
        input_set_generator=MDSetGenerator(
            ensemble="nvt",
            start_temp=temperature,
            end_temp=end_temp,
            nsteps=steps_production,
            time_step=2,
            # adapted from MPMorph settings
            user_incar_settings=incar_settings,
            user_kpoints_settings=gamma_point,
        )
    )

    flow = MPMorphMDMaker(
        convergence_md_maker=EquilibriumVolumeMaker(md_maker=aimd_equil_maker),
        production_md_maker=aimd_prod_maker,
    ).make(structure=intial_structure)

    responses = run_locally(
        flow,
        create_folders=True,
        ensure_success=True,
    )

    uuids = [uuid for uuid in responses]

    ref_md_energies = {
        "energy": [-13.44200043, -35.97470303, -32.48531985],
        "volume": [82.59487098351644, 161.31810738968053, 278.7576895693679],
    }

    # print([responses[uuid][1].output for uuid in responses])
    # print("-----STARTING MPMORPH PRINT-----")
    # print([uuid for uuid in responses])
    # print([responses[uuid][1].output for uuid in responses])
    # print("fit", responses[list(responses)[-2]][1].output)
    # print(
    #    responses[list(responses)[-1]][1].output.output.structure.volume
    # )   # 5.5695648985311683 unit cell
    # print(responses[list(responses)[-1]][1].output.output.energy)
    # print("-----ENDING MPMORPH PRINT-----")
    # asserting False so that stdout is printed by pytest

    assert len(uuids) == 6
    for i in range(len(ref_md_energies["energy"])):
        assert responses[uuids[1 + i]][
            1
        ].output.output.structure.volume == pytest.approx(ref_md_energies["volume"][i])
        assert responses[uuids[1 + i]][1].output.output.energy == pytest.approx(
            ref_md_energies["energy"][i]
        )

    assert isinstance(responses[uuids[4]][1].output, Structure)
    assert responses[uuids[4]][1].output.volume == pytest.approx(171.51227)

    assert responses[uuids[5]][1].output.output.structure.volume == pytest.approx(
        172.7682
    )
    assert responses[uuids[5]][1].output.output.energy == pytest.approx(-38.1286)


def test_mpmorph_vasp_maker(mock_vasp, clean_dir, vasp_test_dir):
    pass


def test_mpmoprh_vasp_slow_quench_maker(mock_vasp, clean_dir, vasp_test_dir):
    pass


def test_mpmorph_vasp_fast_quench_maker(mock_vasp, clean_dir, vasp_test_dir):
    pass
