import math
import os
import sys
import copy
import subprocess
import glob
import xml.etree.ElementTree as ET

def clone_repo(remote):
    os.system('git clone ' + remote)

class Split:
    def __init__(self, part_id, staff_ids, measure_ids):
        self.part_id = part_id
        self.staff_ids = staff_ids
        self.measure_ids = measure_ids

    def __repr__(self) -> str:
        return 'part_id: {}, staff_ids: {}, measure_ids: {}'.format(self.part_id, self.staff_ids, self.measure_ids)

def find_splits(root):
    score = root.find('Score')
    parts = score.findall('./Part')
    splits = []
    for part_id, part in enumerate(parts):
        staff_ids_in_part = [staff.attrib['id'] for staff in part.findall('./Staff')]
        staffs = root.findall('./Score/Staff')
        maintain_staff_ids = []
        for staff in staffs:
            is_in_part = staff.attrib['id'] in staff_ids_in_part
            if not is_in_part:
                continue
            maintain_staff_ids.append(staff.attrib['id'])
            measures = staff.findall('./Measure')
            groups = math.ceil(len(measures) / 4)
            for group in range(groups):
                splits.append(Split(part_id, maintain_staff_ids, range(group * 4, min((group + 1) * 4, len(measures)))))
    return splits

def apply_split(root, split: Split):
    root = copy.deepcopy(root)
    score = root.find('Score')
    for part_id, part in enumerate(score.findall('./Part')):
        if part_id != split.part_id:
            score.remove(part)
            continue
    staff_id = 0
    for staff in score.findall('./Staff'):
        if staff.attrib['id'] not in split.staff_ids:
            score.remove(staff)
            continue
        staff_id += 1
        staff.attrib['id'] = '{}'.format(staff_id)
        for measure_id, measure in enumerate(staff.findall('./Measure')):
            if measure_id not in split.measure_ids:
                staff.remove(measure)
                continue
            for layoutbreak in measure.findall('./LayoutBreak'):
                measure.remove(layoutbreak)
    return root

def split_file(filename):
    folder = os.path.dirname(filename)
    tree = ET.parse(filename)
    root = tree.getroot()
    splits = find_splits(root)
    result = [apply_split(root, split) for split in splits]
    files = []
    for i, r in enumerate(result):
        result_filename = os.path.join(folder, 'split_{}.mscx'.format(i))
        ET.ElementTree(r).write(result_filename)
        files.append(result_filename)
    return files

def convert_file_to_png(filename):
    muse_score_command = "musescore"
    is_windows = sys.platform.startswith('win')
    if is_windows:
        muse_score_command = "C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe"
    png_name = filename.replace('.mscx', '.png')
    subprocess.call([muse_score_command, filename, '-o', png_name])
    print('Converted {} to {}'.format(filename, png_name))

def prepare_folder(folder):
    marker = 'prepare_done.txt'
    if os.path.isfile(os.path.join(folder, marker)):
        return
    files = glob.glob(os.path.join(folder, '**', '*.mscx'), recursive=True)
    for file in files:
        if "split" in file:
            continue
        splits = split_file(file)
        for split in splits:
            convert_file_to_png(split)
    with open(os.path.join(folder, marker), 'w') as f:
        f.write('done')

def download_references():
    if not os.path.isdir('StringQuartets'):
        print('Downloading StringQuartets...')
        clone_repo("https://github.com/OpenScore/StringQuartets")

    if not os.path.isdir('Lieder'):
        print('Downloading Lieder...')
        clone_repo("https://github.com/OpenScore/Lieder")

if __name__ == '__main__':
    download_references()    
    prepare_folder('Lieder/scores/Barnby,_Joseph/')