from typing import Optional, List, Union
from pathlib import Path

from pydantic import BaseModel, Field

from emmet.core.vasp.task_valid import TaskState

import pandas as pd


class CalculationInput(BaseModel, extra="allow"):

    steps: Optional[int] = Field(0, description="Total steps")

    step_size: Optional[float] = Field(None, description="")

    platform_name: Optional[str] = Field(None, description="Platform name")

    platform_properties: Optional[dict] = Field(None, description="Platform properties")

    state_interval: Optional[int] = Field(None, description="")

    dcd_interval: Optional[int] = Field(None, description="Report interval")

    wrap_dcd: Optional[bool] = Field(None, description="Wrap particles or not")

    temperature: Optional[float] = Field(
        None, description="Final temperature for the calculation"
    )

    pressure: Optional[float] = Field(None, description="Pressure for the calculation")

    friction_coefficient: Optional[float] = Field(
        None, description="Friction coefficient for the calculation"
    )


class CalculationOutput(BaseModel):

    dir_name: Optional[str] = Field(
        None, description="The directory for this OpenMM task"
    )

    dcd_file: Optional[str] = Field(
        None, description="Path to the DCD file relative to `dir_name`"
    )

    state_file: Optional[str] = Field(
        None, description="Path to the state file relative to `dir_name`"
    )

    output_steps: Optional[List[int]] = Field(None, description="List of steps")

    time: Optional[List[float]] = Field(None, description="List of times")

    potential_energy: Optional[List[float]] = Field(
        None, description="List of potential energies"
    )

    kinetic_energy: Optional[List[float]] = Field(
        None, description="List of kinetic energies"
    )

    total_energy: Optional[List[float]] = Field(
        None, description="List of total energies"
    )

    temperature: Optional[List[float]] = Field(None, description="List of temperatures")

    volume: Optional[List[float]] = Field(None, description="List of volumes")

    density: Optional[List[float]] = Field(None, description="List of densities")

    elapsed_time: Optional[float] = Field(
        None, description="Elapsed time for the calculation"
    )

    @classmethod
    def from_directory(
        cls,
        dir_name: Path | str,
        elapsed_time: Optional[float] = None,
    ):
        state_file = Path(dir_name) / "state_csv"
        column_name_map = {
            '#"Step"': "output_steps",
            "Potential Energy (kJ/mole)": "potential_energy",
            "Kinetic Energy (kJ/mole)": "kinetic_energy",
            "Total Energy (kJ/mole)": "total_energy",
            "Temperature (K)": "temperature",
            "Box Volume (nm^3)": "volume",
            "Density (g/mL)": "density",
        }
        state_is_not_empty = state_file.exists() and state_file.stat().st_size > 0
        if state_is_not_empty:
            data = pd.read_csv(state_file, header=0)
            data = data.rename(columns=column_name_map)
            data = data.filter(items=column_name_map.values())
            attributes = data.to_dict(orient="list")
            state_file_name = state_file.name
        else:
            attributes = {name: None for name in column_name_map.values()}
            state_file_name = None

        dcd_file = Path(dir_name) / "trajectory_dcd"
        dcd_is_not_empty = dcd_file.exists() and dcd_file.stat().st_size > 0
        dcd_file_name = dcd_file.name if dcd_is_not_empty else None

        return CalculationOutput(
            dir_name=str(dir_name),
            elapsed_time=elapsed_time,
            dcd_file=dcd_file_name,
            state_file=state_file_name,
            **attributes,
        )


class Calculation(BaseModel):

    dir_name: Optional[str] = Field(
        None, description="The directory for this OpenMM calculation"
    )

    has_openmm_completed: Optional[Union[TaskState, bool]] = Field(
        None, description="Whether OpenMM completed the calculation successfully"
    )

    input: Optional[CalculationInput] = Field(
        None, description="OpenMM input settings for the calculation"
    )
    output: Optional[CalculationOutput] = Field(
        None, description="The OpenMM calculation output"
    )

    completed_at: Optional[str] = Field(
        None, description="Timestamp for when the calculation was completed"
    )
    task_name: Optional[str] = Field(
        None, description="Name of task given by custodian (e.g., relax1, relax2)"
    )

    calc_type: Optional[str] = Field(
        None,
        description="Return calculation type (run type + task_type). or just new thing",
    )
