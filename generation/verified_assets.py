"""Render molecular identifiers with a chemistry toolkit instead of guessed line art."""
import hashlib
import re
from pathlib import Path


def molecule_assets(case, output):
    match = re.search(r'InChI=\S+', case.get('prompt_text', ''))
    if not match:
        return None
    from rdkit import Chem
    from rdkit.Chem import rdDepictor, rdMolDescriptors
    from rdkit.Chem.Draw import rdMolDraw2D
    inchi = match.group(0).rstrip('.,;')
    molecule = Chem.MolFromInchi(inchi)
    if molecule is None:
        raise ValueError('Source InChI could not be parsed; refusing guessed structure')
    Chem.AssignStereochemistry(molecule, cleanIt=True, force=True)
    rdDepictor.Compute2DCoords(molecule)
    patterns = {'hydroxyl': '[OX2H]', 'methoxy': '[OX2]([CH3])[#6;!$(C=O)]',
                'ester': '[CX3](=[OX1])[OX2][#6]'}
    colors = {'hydroxyl': (0.95, 0.55, 0.2), 'methoxy': (0.2, 0.7, 0.95), 'ester': (0.65, 0.4, 0.85)}
    groups = {name: [list(m) for m in molecule.GetSubstructMatches(Chem.MolFromSmarts(smarts))]
              for name, smarts in patterns.items()}
    output = Path(output); output.mkdir(exist_ok=True, parents=True)
    paths = {}
    for highlighted in (False, True):
        drawer = rdMolDraw2D.MolDraw2DCairo(1000, 680)
        options = drawer.drawOptions()
        options.baseFontSize = 0.8
        options.fixedFontSize = 34
        atoms, atom_colors = [], {}
        if highlighted:
            for name, matches in groups.items():
                for group in matches:
                    for atom in group:
                        atoms.append(atom); atom_colors[atom] = colors[name]
        drawer.DrawMolecule(molecule, highlightAtoms=sorted(set(atoms)), highlightAtomColors=atom_colors)
        drawer.FinishDrawing()
        path = output / ('molecule_classified.png' if highlighted else 'molecule.png')
        path.write_bytes(drawer.GetDrawingText())
        paths['classified' if highlighted else 'initial'] = str(path.resolve())
    return dict(kind='inchi_molecule', source_inchi=inchi, canonical_inchi=Chem.MolToInchi(molecule),
                inchikey=Chem.MolToInchiKey(molecule), formula=rdMolDescriptors.CalcMolFormula(molecule),
                atom_count=molecule.GetNumAtoms(), stereocenters=Chem.FindMolChiralCenters(molecule, includeUnassigned=True),
                functional_groups=groups, paths=paths,
                sha256={name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name,path in paths.items()},
                instruction='Use self.verified_structure(highlighted=False/True) to show this exact molecule. '
                    'Do not redraw atoms or bonds. Classify only matched functional groups with matching orange hydroxyl, blue methoxy, purple ester labels.')
