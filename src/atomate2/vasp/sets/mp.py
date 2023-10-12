"""
Module defining jobs for Materials Project r2SCAN workflows.

Reference: https://doi.org/10.1103/PhysRevMaterials.6.013801

In case of questions, consult @Andrew-S-Rosen, @esoteric-ephemera or @janosh.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from monty.serialization import loadfn
from pkg_resources import resource_filename

from atomate2.vasp.sets.core import (
    EOSSetGenerator,
    RelaxSetGenerator,
    StaticSetGenerator,
)

if TYPE_CHECKING:
    from pymatgen.core import Structure
    from pymatgen.io.vasp import Outcar, Vasprun

_BASE_MP_GGA_RELAX_SET = loadfn(
    resource_filename("atomate2.vasp.sets", "BaseMPGGASet.yaml")
)
_BASE_MP_R2SCAN_RELAX_SET = loadfn(
    resource_filename("atomate2.vasp.sets", "BaseMPR2SCANRelaxSet.yaml")
)


@dataclass
class MPGGARelaxSetGenerator(RelaxSetGenerator):
    """Class to generate MP-compatible VASP GGA relaxation input sets."""

    config_dict: dict = field(default_factory=lambda: _BASE_MP_GGA_RELAX_SET)
    auto_ismear: bool = False
    auto_kspacing: bool = True
    inherit_incar: bool = False


@dataclass
class MPGGAStaticSetGenerator(StaticSetGenerator):
    """Class to generate MP-compatible VASP GGA static input sets."""

    config_dict: dict = field(default_factory=lambda: _BASE_MP_GGA_RELAX_SET)
    auto_kspacing: bool = True
    inherit_incar: bool = False

    def get_incar_updates(
        self,
        structure: Structure,
        prev_incar: dict = None,
        bandgap: float = None,
        vasprun: Vasprun = None,
        outcar: Outcar = None,
    ) -> dict:
        """
        Get updates to the INCAR for this calculation type.

        Parameters
        ----------
        structure
            A structure.
        prev_incar
            An incar from a previous calculation.
        bandgap
            The band gap.
        vasprun
            A vasprun from a previous calculation.
        outcar
            An outcar from a previous calculation.

        Returns
        -------
        dict
            A dictionary of updates to apply.
        """
        return {
            "ALGO": "FAST",
            "NSW": 0,
            "LCHARG": True,
            "LWAVE": False,
            "LREAL": False,
            "ISMEAR": -5,
        }


@dataclass
class MPGGAEOSSetGenerator(EOSSetGenerator):
    """Class to generate MP-compatible VASP GGA EOS input sets."""

    config_dict: dict = field(default_factory=lambda: _BASE_MP_GGA_RELAX_SET)
    auto_ismear: bool = False
    auto_kspacing: bool = True
    inherit_incar: bool = False


@dataclass
class MPMetaGGAStaticSetGenerator(StaticSetGenerator):
    """Class to generate MP-compatible VASP GGA static input sets."""

    config_dict: dict = field(default_factory=lambda: _BASE_MP_R2SCAN_RELAX_SET)
    auto_ismear: bool = False
    auto_kspacing: bool = True
    inherit_incar: bool = False

    def get_incar_updates(
        self,
        structure: Structure,
        prev_incar: dict = None,
        bandgap: float = None,
        vasprun: Vasprun = None,
        outcar: Outcar = None,
    ) -> dict:
        """
        Get updates to the INCAR for this calculation type.

        Parameters
        ----------
        structure
            A structure.
        prev_incar
            An incar from a previous calculation.
        bandgap
            The band gap.
        vasprun
            A vasprun from a previous calculation.
        outcar
            An outcar from a previous calculation.

        Returns
        -------
        dict
            A dictionary of updates to apply.
        """
        return {
            "ALGO": "FAST",
            "GGA": None,  # unset GGA, shouldn't be set anyway but best be sure
            "NSW": 0,
            "LCHARG": True,
            "LWAVE": False,
            "LREAL": False,
            "ISMEAR": -5,
        }


@dataclass
class MPMetaGGARelaxSetGenerator(RelaxSetGenerator):
    """Class to generate MP-compatible VASP metaGGA relaxation input sets.

    Parameters
    ----------
    config_dict: dict
        The config dict.
    bandgap_tol: float
        Tolerance for metallic bandgap. If bandgap < bandgap_tol, KSPACING will be 0.22,
        otherwise it will increase with bandgap up to a max of 0.44.
    bandgap_override: float | None
        Override the bandgap with a fixed value. Defaults to None.
    """

    config_dict: dict = field(default_factory=lambda: _BASE_MP_R2SCAN_RELAX_SET)
    bandgap_tol: float = 1e-4
    bandgap_override: float | None = None
    auto_ismear: bool = False
    auto_kspacing: bool = True
    inherit_incar: bool = False

    def get_incar_updates(
        self,
        structure: Structure,
        prev_incar: dict = None,
        bandgap: float = None,
        vasprun: Vasprun = None,
        outcar: Outcar = None,
    ) -> dict:
        """
        Get updates to the INCAR for this calculation type.

        Parameters
        ----------
        structure
            A structure.
        prev_incar
            An incar from a previous calculation.
        bandgap
            The band gap.
        vasprun
            A vasprun from a previous calculation.
        outcar
            An outcar from a previous calculation.

        Returns
        -------
        dict
            A dictionary of updates to apply.
        """
        # unset GGA, shouldn't be set anyway but doesn't hurt to be sure
        return {"LCHARG": True, "LWAVE": True, "GGA": None}
