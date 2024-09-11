"""Utilities for working with the OPLS forcefield in OpenMM."""

from __future__ import annotations

import copy
import io
import re
import tempfile
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree
from xml.etree.ElementTree import tostring

import numpy as np
import openff.toolkit as tk
from emmet.core.openmm import OpenMMTaskDocument
from openff.units import unit
from openmm.app import ForceField
from openmm.app.forcefield import PME
from pymatgen.core import Element
from pymatgen.io.openff import get_atom_map

if TYPE_CHECKING:
    from openmm import System


class XMLMoleculeFF:
    """A class for manipulating XML files representing OpenMM-compatible forcefields."""

    def __init__(self, xml_string: str) -> None:
        """Create an XMLMoleculeFF object from a string version of the XML file."""
        self.tree = ElementTree.parse(io.StringIO(xml_string))  # noqa: S314

    def __str__(self) -> str:
        """Return the a string version of the XML file."""
        return tostring(self.tree.getroot(), encoding="unicode")

    def increment_types(self, increment: str) -> None:
        """Increment the type names in the XMLMoleculeFF object.

        This method is needed because LigParGen will reuse type names
        in XML files, then causing an error in OpenMM. We differentiate
        the types with this method.
        """
        root_type = [
            (".//AtomTypes/Type", "name"),
            (".//AtomTypes/Type", "class"),
            (".//Residues/Residue/Atom", "type"),
            (".//HarmonicBondForce/Bond", "class"),
            (".//HarmonicAngleForce/Angle", "class"),
            (".//PeriodicTorsionForce/Proper", "class"),
            (".//PeriodicTorsionForce/Improper", "class"),
            (".//NonbondedForce/Atom", "type"),
        ]
        for xpath, type_stub in root_type:
            for element in self.tree.getroot().findall(xpath):
                for key in element.attrib:
                    if type_stub in key:
                        element.attrib[key] += increment

    def to_openff_molecule(self) -> tk.Molecule:
        """Convert the XMLMoleculeFF to an openff_toolkit Molecule."""
        if sum(self.partial_charges) > 0:
            # TODO: update message
            warnings.warn("Formal charges not considered.", stacklevel=1)

        p_table = {e.symbol: e.number for e in Element}
        openff_mol = tk.Molecule()
        for atom in self.tree.getroot().findall(".//Residues/Residue/Atom"):
            symbol = atom.attrib["name"][0]  # TODO: replace with character regex
            atomic_number = p_table[symbol]
            openff_mol.add_atom(atomic_number, formal_charge=0, is_aromatic=False)

        for bond in self.tree.getroot().findall(".//Residues/Residue/Bond"):
            openff_mol.add_bond(
                int(bond.attrib["from"]),
                int(bond.attrib["to"]),
                bond_order=1,
                is_aromatic=False,
            )

        openff_mol.partial_charges = self.partial_charges * unit.elementary_charge

        return openff_mol

    @property
    def partial_charges(self) -> np.ndarray:
        """Get the partial charges from the XMLMoleculeFF object."""
        atoms = self.tree.getroot().findall(".//NonbondedForce/Atom")
        charges = [float(atom.attrib["charge"]) for atom in atoms]
        return np.array(charges)

    @partial_charges.setter
    def partial_charges(self, partial_charges: np.ndarray) -> None:
        for i, atom in enumerate(self.tree.getroot().findall(".//NonbondedForce/Atom")):
            atom.attrib["charge"] = str(partial_charges[i])

    def assign_partial_charges(self, mol_or_method: tk.Molecule | str) -> None:
        """Assign partial charges to the XMLMoleculeFF object.

        Parameters
        ----------
        mol_or_method : Union[tk.Molecule, str]
            If a molecule is provided, it must have partial charges assigned.
            If a string is provided, openff_toolkit.Molecule.assign_partial_charges
            will be used to generate the partial charges.

        """
        if isinstance(mol_or_method, str):
            openff_mol = self.to_openff_molecule()
            openff_mol.assign_partial_charges(mol_or_method)
            mol_or_method = openff_mol
        self_mol = self.to_openff_molecule()
        isomorphic, atom_map = get_atom_map(mol_or_method, self_mol)
        mol_charges = mol_or_method.partial_charges[list(atom_map.values())].magnitude
        self.partial_charges = mol_charges

    def to_file(self, file: str | Path) -> None:
        """Write the XMLMoleculeFF object to an XML file."""
        self.tree.write(file, encoding="utf-8")

    @classmethod
    def from_file(cls, file: str | Path) -> XMLMoleculeFF:
        """Create an XMLMoleculeFF object from an XML file."""
        with open(file) as f:
            xml_str = f.read()
        return cls(xml_str)


def create_system_from_xml(
    topology: tk.Topology,
    xml_mols: list[XMLMoleculeFF],
) -> System:
    """Create an OpenMM system from a list of molecule specifications and XML files."""
    io_files = []
    for i, xml in enumerate(xml_mols):
        xml_copy = copy.deepcopy(xml)
        xml_copy.increment_types(f"_{i}")
        io_files.append(io.StringIO(str(xml_copy)))

    ff = ForceField(io_files[0])
    for i, xml in enumerate(io_files[1:]):  # type: ignore[assignment]
        ff.loadFile(xml, resname_prefix=f"_{i + 1}")

    return ff.createSystem(topology.to_openmm(), nonbondedMethod=PME)


def download_opls_xml(
    names_smiles: dict[str, str], output_dir: str | Path, overwrite_files: bool = False
) -> None:
    """Download an OPLS-AA/M XML file from the LigParGen website using Selenium."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager

    except ImportError:
        warnings.warn(
            "The `selenium` package is not installed. "
            "It's required to run the opls web scraper.",
            stacklevel=1,
        )

    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    for name, smiles in names_smiles.items():
        final_file = Path(output_dir) / f"{name}.xml"
        if final_file.exists() and not overwrite_files:
            continue
        try:
            # Specify the directory where you want to download files
            with tempfile.TemporaryDirectory() as tmpdir:
                download_dir = tmpdir

                # Set up Chrome options
                chrome_options = webdriver.ChromeOptions()
                prefs = {"download.default_directory": download_dir}
                chrome_options.add_experimental_option("prefs", prefs)

                # Initialize Chrome with the options
                driver = webdriver.Chrome(options=chrome_options)

                # Open the first webpage
                driver.get("https://zarbi.chem.yale.edu/ligpargen/")

                # Find the SMILES input box and enter the SMILES code
                smiles_input = driver.find_element(By.ID, "smiles")
                smiles_input.send_keys(smiles)

                # Find and click the "Submit Molecule" button
                submit_button = driver.find_element(
                    By.XPATH,
                    '//button[@type="submit" and contains(text(), "Submit Molecule")]',
                )
                submit_button.click()

                # Wait for the second page to load
                # time.sleep(2)  # Adjust this delay as needed based on the loading time

                # Find and click the "XML" button under Downloads and OpenMM
                xml_button = driver.find_element(
                    By.XPATH, '//input[@type="submit" and @value="XML"]'
                )
                xml_button.click()

                # Wait for the file to download
                time.sleep(0.3)  # Adjust as needed based on the download time

                file = next(Path(tmpdir).iterdir())
                # copy downloaded file to output_file using os
                Path(file).rename(final_file)

        except Exception as e:  # noqa: BLE001
            warnings.warn(
                f"{name} ({smiles}) failed to download because an error occurred: {e}",
                stacklevel=1,
            )

    driver.quit()


def create_list_summing_to(total_sum: int, n_pieces: int) -> list:
    """Create a NumPy array with n_pieces elements that sum up to total_sum.

    Divides total_sum by n_pieces to determine the base value for each element.
    Distributes the remainder evenly among the elements.

    Parameters
    ----------
    total_sum : int
        The desired sum of the array elements.
    n_pieces : int
        The number of elements in the array.

    Returns
    -------
    numpy.ndarray
        A 1D NumPy array with n_pieces elements summing up to total_sum.
    """
    div, mod = total_sum // n_pieces, total_sum % n_pieces
    return [div + 1] * mod + [div] * (n_pieces - mod)


def increment_name(file_name: str) -> str:
    """Increment the count in a file name."""
    # logic to increment count on file name
    re_match = re.search(r"(\d*)$", file_name)
    position = re_match.start(1)
    new_count = int(re_match.group(1) or 1) + 1
    return f"{file_name[:position]}{new_count}"


def task_reports(task: OpenMMTaskDocument, traj_or_state: str = "traj") -> bool:
    """Check if a task reports trajectories or states."""
    if not task.calcs_reversed:
        return False
    calc_input = task.calcs_reversed[0].input
    if traj_or_state == "traj":
        report_freq = calc_input.traj_interval
    elif traj_or_state == "state":
        report_freq = calc_input.state_interval
    else:
        raise ValueError("traj_or_state must be 'traj' or 'state'")
    return calc_input.n_steps >= report_freq
