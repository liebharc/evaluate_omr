import math
import os
import sys
import copy
import subprocess
import glob
import difflib
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
        last_key_sig = None
        first_measure = True
        for measure_id, measure in enumerate(staff.findall('./Measure')):
            if measure_id not in split.measure_ids:
                measure_key_sig = measure.find('./voice/KeySig')
                if measure_key_sig is not None:
                    last_key_sig = measure_key_sig
                staff.remove(measure)
                continue
            for layoutbreak in measure.findall('./LayoutBreak'):
                measure.remove(layoutbreak)
            measure_key_sig = measure.find('./voice/KeySig')
            if measure_key_sig is None and last_key_sig is not None and first_measure:
                voice = measure.find('./voice')
                first_measure = False
                if voice is not None:
                    voice.insert(0, last_key_sig)
            last_key_sig = measure_key_sig
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
    return png_name

def prepare_folder(folder):
    marker = 'prepare_done.txt'
    if os.path.isfile(os.path.join(folder, marker)):
        return glob.glob(os.path.join(folder, '**', 'split*.png'), recursive=True)
    files = glob.glob(os.path.join(folder, '**', '*.mscx'), recursive=True)
    png_files = []
    for file in files:
        if "split" in file:
            continue
        splits = split_file(file)
        for split in splits:
            png_files.append(convert_file_to_png(split))
    with open(os.path.join(folder, marker), 'w') as f:
        f.write('done')

    return png_files

def download_references():
    if not os.path.isdir('StringQuartets'):
        print('Downloading StringQuartets...')
        clone_repo("https://github.com/OpenScore/StringQuartets")

    if not os.path.isdir('Lieder'):
        print('Downloading Lieder...')
        clone_repo("https://github.com/OpenScore/Lieder")

def key_sig_node_to_string(key_sig):
    accidential = key_sig.find('./accidental')
    return "Key {}".format(accidential.text) if accidential is not None else "Key C"

def rest_node_to_string(rest):
    duration = rest.find('./duration')
    return 'Rest {}'.format(duration.text) if duration is not None else 'Rest'

def chord_node_to_string(chord):
    note = chord.find('./Note')
    pitch = note.find('./pitch')
    return 'Note {}'.format(pitch.text) if pitch is not None else 'Note'

def get_key_and_notes_from_musicxml(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    staffs = root.findall('./Score/Staff')
    result = []
    for staff in staffs:
        measures = staff.findall('./Measure')
        for measure in measures:
            voice = measure.find('./voice')
            if voice is None:
                continue
            for child in voice:
                if child.tag == 'KeySig':
                    result.append(key_sig_node_to_string(child))
                elif child.tag == 'Rest':
                    result.append(rest_node_to_string(child))
                elif child.tag == 'Chord':
                    result.append(chord_node_to_string(child))
    print(result)
    return result

def compare_result(result, reference):
    def count_not_equal_of_codes(codes):
        differences = [code for code in codes if code[0] != "equal"]
        sum = 0
        for difference in differences:
            sum += max(difference[4] - difference[3], difference[2] - difference[1])
        return sum

    result_content = get_key_and_notes_from_musicxml(result)
    reference_content = get_key_and_notes_from_musicxml(reference)
    diffs = difflib.SequenceMatcher(None, result_content, reference_content)
    number_of_diffs = count_not_equal_of_codes(diffs.get_opcodes())
    print('Comparing {} with {}: {}'.format(result, reference, number_of_diffs))  
    return number_of_diffs

def run_omr(filename: str) -> str:
    """
    Runs OMR on the given file and returns the result: Replace it with the OMR system you want to evaluate.
    """
    if os.system("oemer --use-tf " + filename) != 0:
        print("Error running OMR on " + filename)
        return None
    return filename.replace('.png', '.musicxml')

if __name__ == '__main__':
    download_references()    
    image_files = prepare_folder('Lieder/scores/Barnby,_Joseph/')
    sum_of_diffs = 0
    # Also count complete failures where we didn't get a result
    sum_of_failures = 0 
    for image_file in image_files:
        print('Running OMR on {}'.format(image_file))
        reference = image_file.replace('-1.png', '.mscx')
        result = run_omr(image_file)
        if result is None:
            print('Error running OMR on {}'.format(image_file))
            sum_of_failures += 1
            continue
        sum_of_diffs += compare_result(result, reference)
