"""Define general ASE-calculator jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from jobflow import Maker, job
import logging
import os
from typing import TYPE_CHECKING

from ase.io import Trajectory as AseTrajectory
from atomate2.ase.schemas import AseTaskDocument
from atomate2.ase.utils import AseRelaxer
from pymatgen.core.trajectory import Trajectory as PmgTrajectory

logger = logging.getLogger(__name__)

_ASE_DATA_OBJECTS = [PmgTrajectory, AseTrajectory]

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Callable
    from ase.calculators.calculator import Calculator

    from pymatgen.core import Structure


def ase_job(method: Callable) -> job:
    """
    Decorate the ``make`` method of ASE job makers.

    This is a thin wrapper around :obj:`~jobflow.core.job.Job` that configures common
    settings for all ASE jobs. For example, it ensures that large data objects
    (currently only trajectories) are all stored in the atomate2 data store.
    It also configures the output schema to be a AseTaskDocument :obj:`.TaskDoc`.

    Any makers that return ASE jobs (not flows) should decorate the
    ``make`` method with @ase_job. For example:

    .. code-block:: python

        class MyAseMaker(Maker):
            @ase_job
            def make(structure):
                # code to run ase job.
                pass

    Parameters
    ----------
    method : callable
        A Maker.make method. This should not be specified directly and is
        implied by the decorator.

    Returns
    -------
    callable
        A decorated version of the make function that will generate forcefield jobs.
    """
    return job(
        method, data=_ASE_DATA_OBJECTS, output_schema=AseTaskDocument
    )

@dataclass
class AseRelaxMaker(Maker):
    """
    Base Maker to calculate forces and stresses using any ASE calculator.

    Should be subclassed to use a specific ASE. The user should
    define `self.calculator` when subclassing.

    Parameters
    ----------
    name : str
        The job name.
    relax_cell : bool = True
        Whether to allow the cell shape/volume to change during relaxation.
    fix_symmetry : bool = False
        Whether to fix the symmetry during relaxation.
        Refines the symmetry of the initial structure.
    symprec : float = 1e-2
        Tolerance for symmetry finding in case of fix_symmetry.
    steps : int
        Maximum number of ionic steps allowed during relaxation.
    relax_kwargs : dict
        Keyword arguments that will get passed to :obj:`AseRelaxer.relax`.
    optimizer_kwargs : dict
        Keyword arguments that will get passed to :obj:`AseRelaxer()`.
    calculator_kwargs : dict
        Keyword arguments that will get passed to the ASE calculator.
    task_document_kwargs : dict
        Additional keyword args passed to :obj:`.ForceFieldTaskDocument()`.
    """

    name: str = "ASE relaxation"
    relax_cell: bool = True
    fix_symmetry: bool = False
    symprec: float = 1e-2
    steps: int = 500
    relax_kwargs: dict = field(default_factory=dict)
    optimizer_kwargs: dict = field(default_factory=dict)
    calculator_kwargs: dict = field(default_factory=dict)
    task_document_kwargs: dict = field(default_factory=dict)

    @ase_job
    def make(
        self, structure: Structure, prev_dir: str | Path | None = None
    ) -> AseTaskDocument:
        """
        Relax a structure using ASE.

        Parameters
        ----------
        structure: .Structure
            pymatgen structure.
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
                added to match the method signature of other makers.
        """
        if self.steps < 0:
            logger.warning(
                "WARNING: A negative number of steps is not possible. "
                "Behavior may vary..."
            )
        self.task_document_kwargs.setdefault("dir_name", os.getcwd())

        relaxer = AseRelaxer(
            self.calculator,
            relax_cell=self.relax_cell,
            fix_symmetry=self.fix_symmetry,
            symprec=self.symprec,
            **self.optimizer_kwargs,
        )
        result = relaxer.relax(structure, steps=self.steps, **self.relax_kwargs)

        return AseTaskDocument.from_ase_compatible_result(
            getattr(self.calculator,"name",self.calculator.__class__),
            result,
            self.relax_cell,
            self.steps,
            self.relax_kwargs,
            self.optimizer_kwargs,
            self.fix_symmetry,
            self.symprec,
            **self.task_document_kwargs,
        )

    @property
    def calculator(self) -> Calculator:
        """ASE calculator, can be overwritten by user."""
        return NotImplemented
    
class LennardJonesRelaxMaker(AseRelaxMaker):

    name: str = "Lennard-Jones 6-12 relaxation"

    @property
    def calculator(self) -> Calculator:
        from ase.calculators.lj import LennardJones
        return LennardJones(**self.calculator_kwargs)

class GFNxTBRelaxMaker(AseRelaxMaker):

    name: str = "GFNxTB relaxation"
    calculator_kwargs: dict = field(
        default_factory={
            "method": "GFN2-xTB",
            "charge": None,
            "multiplicity": None,
            "accuracy": 1.0,
            "guess": "sad",
            "max_iterations": 250,
            "mixer_damping": 0.4,
            "electric_field": None,
            "spin_polarization": None,
            "electronic_temperature": 300.0,
            "cache_api": True,
            "verbosity": 1,
        }
    )

    @property
    def calculator(self) -> Calculator:
        from tblite.ase import TBLite
        return TBLite(atoms = None, **self.calculator_kwargs)