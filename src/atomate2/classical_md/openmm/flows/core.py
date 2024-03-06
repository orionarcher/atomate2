from tempfile import TemporaryDirectory
from atomate2.openmm.jobs.energy_minimization_maker import EnergyMinimizationMaker
from atomate2.openmm.jobs.npt_maker import NPTMaker
from atomate2.openmm.jobs.temp_change_maker import TempChangeMaker
from atomate2.openmm.jobs.nvt_maker import NVTMaker
from atomate2.openmm.flows.anneal_maker import AnnealMaker
from typing import Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from jobflow import Maker, Flow
from atomate2.openmm.jobs.base_openmm_maker import BaseOpenMMMaker
from typing import Dict, Tuple
from openmm import Platform
from openmm.app import DCDReporter
from openmm.unit import kelvin
import os
import numpy as np
from pydantic import Field




@dataclass
class ProductionMaker(Maker):
    """
    Class for running
    """
    name: str = "production"
    energy_maker: EnergyMinimizationMaker = field(default_factory=EnergyMinimizationMaker)
    npt_maker: NPTMaker = field(default_factory=NPTMaker)
    anneal_maker: AnnealMaker = field(default_factory=AnnealMaker)
    nvt_maker: NVTMaker = field(default_factory=NVTMaker)

    def make(self, input_set: OpenMMSet, output_dir: Optional[Union[str, Path]] = None):
        """

        Parameters
        ----------
        input_set : OpenMMSet
            OpenMMSet object instance.
        output_dir : Optional[Union[str, Path]]
            File path to directory for writing simulation output files (e.g. trajectory and state files)

        Returns
        -------

        """
        if output_dir is None:
            # TODO: will temp_dir close properly? When will it close?
            temp_dir = TemporaryDirectory()
            output_dir = temp_dir.name
            output_dir = Path(output_dir)
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        energy_job = self.energy_maker.make(
            input_set=input_set,
            output_dir=output_dir / f"0_{self.energy_maker.name.replace(' ', '_')}"
        )

        pressure_job = self.npt_maker.make(
            input_set=energy_job.output.calculation_output.input_set,
            output_dir=output_dir / f"1_{self.npt_maker.name.replace(' ', '_')}"
        )

        anneal_job = self.anneal_maker.make(
            input_set=pressure_job.output.calculation_output.input_set,
            output_dir=output_dir / f"2_{self.anneal_maker.name.replace(' ', '_')}"
        )

        nvt_job = self.nvt_maker.make(
            input_set=anneal_job.output.calculation_output.input_set,
            output_dir=output_dir / f"3_{self.nvt_maker.name.replace(' ', '_')}"
        )

        my_flow = Flow(
            [
                energy_job,
                pressure_job,
                anneal_job,
                nvt_job,
            ],
            output={"log": nvt_job},
        )

        return my_flow

    @classmethod
    def make_from(cls):
        return

@dataclass
class AnnealMaker(Maker):
    """
    steps : Union[Tuple[int, int, int], int]
    """

    name: str = "anneal"
    raise_temp_maker: TempChangeMaker = field(default_factory=lambda: TempChangeMaker(final_temp=400))
    nvt_maker: NVTMaker = field(default_factory=NPTMaker)
    lower_temp_maker: TempChangeMaker = field(default_factory=TempChangeMaker)

    @classmethod
    def from_temps_and_steps(
        cls,
        name: str = "anneal",
        anneal_temp: int = 400,
        final_temp: int = 298,
        steps: Union[int, Tuple[int, int, int]] = 1500000,
        temp_steps: Union[int, Tuple[int, int, int]] = 100,
        job_names: Tuple[str, str, str] = ("raise temp", "hold temp", "lower temp"),
        base_kwargs: Dict = None,
    ):
        if isinstance(steps, int):
            steps = (steps // 3, steps // 3, steps - 2 * (steps // 3))
        if isinstance(temp_steps, int):
            temp_steps = (temp_steps, temp_steps, temp_steps)

        raise_temp_maker = TempChangeMaker(
            steps=steps[0],
            name=job_names[0],
            final_temp=anneal_temp,
            temp_steps=temp_steps[0],
            **base_kwargs
        )
        nvt_maker = NVTMaker(
            steps=steps[1],
            name=job_names[1],
            temperature=anneal_temp,
            **base_kwargs
        )
        lower_temp_maker = TempChangeMaker(
            steps=steps[2],
            name=job_names[2],
            final_temp=final_temp,
            temp_steps=temp_steps[2],
            **base_kwargs
        )
        return cls(
            name=name,
            raise_temp_maker=raise_temp_maker,
            nvt_maker=nvt_maker,
            lower_temp_maker=lower_temp_maker,
        )

    def make(
        self,
        input_set: OpenMMSet,
        output_dir: Optional[Union[str, Path]] = None,
        platform: Optional[Union[str, Platform]] = "CPU",
        platform_properties: Optional[Dict[str, str]] = None,
    ):
        """
        Anneal the simulation at the specified temperature.

        Annealing takes place in 3 stages, heating, holding, and cooling. The three
        elements of steps specify the length of each stage. After heating, and holding,
        the system will cool to its original temperature.

        Parameters
        ----------
        input_set : OpenMMSet
            A pymatgen structure object.
        output_dir : str
            Directory to write reporter files to.
        platform : Optional[Union[str, openmm.openmm.Platform]]
             platform: the OpenMM platform passed to the Simulation.
        platform_properties : Optional[Dict[str, str]]
            properties of the OpenMM platform that is passed to the simulation.

        Returns
        -------
        Job
            A OpenMM job containing one npt run.
        """
        if output_dir is None:
            # TODO: will temp_dir close properly? When will it close?
            temp_dir = TemporaryDirectory()
            output_dir = temp_dir.name
            output_dir = Path(output_dir)
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        raise_temp_job = self.raise_temp_maker.make(
            input_set=input_set,
            output_dir=output_dir / f"0_{self.raise_temp_maker.name.replace(' ', '_')}",
        )
        nvt_job = self.nvt_maker.make(
            input_set=raise_temp_job.output.calculation_output.input_set,
            output_dir=output_dir / f"1_{self.nvt_maker.name.replace(' ', '_')}"
        )
        lower_temp_job = self.lower_temp_maker.make(
            input_set=nvt_job.output.calculation_output.input_set,
            output_dir=output_dir / f"2_{self.lower_temp_maker.name.replace(' ', '_')}",
        )

        return Flow([raise_temp_job, nvt_job, lower_temp_job], output=lower_temp_job.output)
