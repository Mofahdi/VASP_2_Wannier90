import os
import numpy as np 
from monty.io import zopen
from monty.json import MSONable
from monty.serialization import loadfn
import warnings

from pymatgen.core.structure import Structure
from pymatgen.io.vasp import Vasprun
from pymatgen.io.vasp.inputs import Potcar
from jarvis.core.kpoints import Kpoints3D
from jarvis.core.atoms import Atoms


def get_POTCAR_symbols(POTCAR_input: str) -> list:
	potcar=Potcar.from_file("POTCAR")
	Potcar_names = [name["symbol"] for name in potcar.spec]
	return Potcar_names

def get_basis(structure: Structure, potcar_input, basis_file_dir=None) -> dict:
	num_atoms_dict={}
	for el, amt in structure.composition.items():
		num_atoms_dict[el.symbol]=amt
		
	Potcar_names=get_POTCAR_symbols(potcar_input)
	AtomTypes_Potcar = [name.split("_")[0] for name in Potcar_names]
	AtomTypes = structure.symbol_set
	if set(AtomTypes) != set(AtomTypes_Potcar):
		raise OSError("Your POSCAR does not correspond to your POTCAR!")
	BASIS = loadfn(basis_file_dir)["BASIS"]
	basis_dict={}
	for itype, type in enumerate(Potcar_names):
		basis_list=BASIS[type].split(); 
		orbitals_list=[basis[1] for basis in basis_list];
		basis_dict.update({AtomTypes_Potcar[itype]: orbitals_list})
	return basis_dict, num_atoms_dict

def get_band_kpoints(path) -> list:
	atoms = Atoms.from_poscar(path)
	#print(atoms.__dict__)
	hi_kp=Kpoints3D().high_kpath(atoms=atoms)
	#lines='begin kpoint_path'
	lines=[]; lines.append('begin kpoint_path\n')
	for i_path in range(len(hi_kp['path'])):
		for hi_symm_kpt_i, hi_symm_kpt in enumerate(hi_kp['path'][i_path]):
			i_hi_fcoord=hi_kp['kpoints'][hi_kp['path'][i_path][hi_symm_kpt_i]]
			f_hi_fcoord=hi_kp['kpoints'][hi_kp['path'][i_path][hi_symm_kpt_i+1]]
			i_hi_kpt=hi_kp['path'][i_path][hi_symm_kpt_i]
			f_hi_kpt=hi_kp['path'][i_path][hi_symm_kpt_i+1]
			#if i_hi_kpt=='\\Gamma':
			#	i_hi_kpt='G'
			i_hi_kpt= 'G' if hi_kp['path'][i_path][hi_symm_kpt_i]=='\\Gamma' else hi_kp['path'][i_path][hi_symm_kpt_i]
			f_hi_kpt= 'G' if hi_kp['path'][i_path][hi_symm_kpt_i+1]=='\\Gamma' else hi_kp['path'][i_path][hi_symm_kpt_i+1]
			hi_kpt_i=i_hi_kpt+' '+str(i_hi_fcoord[0])+' '+str(i_hi_fcoord[1])+' '+str(i_hi_fcoord[2])
			hi_kpt_f=f_hi_kpt+' '+str(f_hi_fcoord[0])+' '+str(f_hi_fcoord[1])+' '+str(f_hi_fcoord[2])
			line=hi_kpt_i+'\t'+hi_kpt_f+'\n'
			lines.append(line)
			
			if hi_symm_kpt_i==len(hi_kp['path'][i_path])-2:
				break
	lines.append('end kpoint_path')
	#lines=lines+'end kpoint_path'
	return lines
	

def write_wan_projections(basis_dict, num_atoms_dict, other_commands=None, POSCAR_path=None,
band_points=30, projection_type='orbitals', file_name='wannier90.win', SOC=True):
	f=open(file_name, mode='w')
	f.write('Begin Projections\n')
	num_wan=0
	for specie, orbitals in basis_dict.items():
		specie_proj='{specie}:'.format(specie=specie)
		specie_l_proj=specie_proj
		for orbital in orbitals:
			if orbital=='s':
				num_wan+=2*num_atoms_dict[specie]
				specie_proj=specie_proj+'s;'
				specie_l_proj=specie_l_proj+"l=0,mr=1;"
			if orbital=='p':
				num_wan+=6*num_atoms_dict[specie]
				specie_proj=specie_proj+'p;'
				specie_l_proj=specie_l_proj+"l=1,mr=1,2,3;"
			if orbital=='d':
				num_wan+=10*num_atoms_dict[specie]
				specie_proj=specie_proj+'d;'
				specie_l_proj=specie_l_proj+"l=2,mr=1,2,3,4,5;"
			if orbital=='f':
				num_wan+=14*num_atoms_dict[specie]
				specie_proj=specie_proj+'f;'
				specie_l_proj=specie_l_proj+"l=3,mr=1,2,3,4,5,6,7;"
		specie_proj=specie_proj[:-1]
		specie_l_proj=specie_l_proj[:-1]
		if projection_type=='orbitals':
			f.write('%s\n'%(specie_proj))
		elif projection_type!='orbitals':
			f.write('%s\n'%(specie_l_proj))
	f.write('End Projections\n')
	if SOC==True:
		num_wan_used=num_wan
	elif SOC==False:
		num_wan_used=num_wan/2
	f.write('num_wann ='+str(int(num_wan_used))+'\n')
	#print(other_commands)
	if other_commands:
		for key, val in other_commands.items():
			f.write(key+' = '+str(val)+'\n')
			if key=='bands_plot' and val=='true':
				kpoints_path=get_band_kpoints(POSCAR_path)
				f.write('bands_num_points = '+str(band_points)+'\n')
				for line in kpoints_path:
					f.write(line)
	
	f.close()

if __name__=="__main__":
	basis_dict, num_atoms_dict=get_basis(structure=Structure.from_file('POSCAR'), potcar_input='POTCAR', \
			basis_file_dir=os.path.join(os.getcwd(), "lobster_basis/BASIS_PBE_54_standard.yaml"))
	wan_commands={' num_iter': 300, 'write_xyz': 'true',  'write_hr': 'true', 'bands_plot': 'true'}
	write_wan_projections(basis_dict, num_atoms_dict, wan_commands, 'POSCAR', file_name='wannier90_test.win')
	
