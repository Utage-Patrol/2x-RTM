from typing import NamedTuple

import json
import os
import pathlib
import re
import struct

SCALE: float = 2.0


class RtmBoneTransform(NamedTuple):
    boneName: str
    transform: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]

class RtmFrame(NamedTuple):
    frameTime: float
    bones: list[RtmBoneTransform]

class RtmData(NamedTuple):
    absolute_offset: tuple[float, float, float] # absolute offset vector
    bones: list[str] # bones list
    frames: list[RtmFrame] # frames list


def read_rtm(
    file, verbose=False
) -> RtmData:
    signature = struct.unpack('8s', file.read(8))[0]
    print(f"Read signature: {signature}")
  
    if signature == b'RTM_MDAT': # Sometimes RTM files contain this signature, too. Or something. I don't really know what I'm doing.
         counter = 0
         print("Found RTM_MDAT")
         buffer = b''

         while True:
            counter += 1
            chunk = file.read(8)
            if not chunk:
                raise Exception(f"Reached end of file without finding {b'RTM_0101'}")
            buffer += chunk
            pos = buffer.find(b'RTM_0101')
            if pos != -1:
                print(buffer)
                print(pos)
                print("READING")
                file.seek((counter-1)*8+pos)
                signature = file.read(8)
                print(signature)
                break
            buffer = buffer[-8:]

    if signature != b'RTM_0101':
        if signature.startswith(b'BMTR'):
            raise Exception('Expected non-binarised RTM but got binary RTM')
        else:
            raise Exception('Cannot parse RTM')
    absolut_vector = struct.unpack('3f', file.read(12))
    nFrames, nBones = struct.unpack('II', file.read(8))
    if verbose:
        print('Frames:', nFrames)
        print('Bones:', nBones)
        print('absolut:', absolut_vector)
    bones = []
    frames = []
    for i in range(0, nBones):
        bone = struct.unpack('32s', file.read(32))[0].split(sep=b'\0',
                                                            maxsplit=1)[0].decode().lower()
        bones.append(bone)
    if verbose:
        print('Bones:')
        for b in bones:
            print(b)

    for f in range(0, nFrames):
        frameTime = struct.unpack('f', file.read(4))[0]
        frameBones = []
        for i in range(0, nBones):
            bone = struct.unpack('32s', file.read(32))[0].split(sep=b'\0',
                                                                maxsplit=1)[0].decode().lower()
            matrix = struct.unpack('12f', file.read(48))
            frameBones.append(RtmBoneTransform(
                boneName=bone,
                transform=(
                    tuple(matrix[0:3]),
                    tuple(matrix[3:6]),
                    tuple(matrix[6:9]),
                    tuple(matrix[9:12]),
                )
            ))
        frames.append(RtmFrame(
            frameTime=frameTime,
            bones=frameBones
        ))

    if verbose:
        print('Frames:')
        for frame in frames:
            print('Frame {}:'.format(frame['frameTime']))
            for bone, matrix in (frame['frameData']).items():
                print(bone, '\n', matrix[0:4], '\n', matrix[4:8], '\n', matrix[8:])

    return RtmData(
        absolute_offset=absolut_vector,
        bones=bones,
        frames=frames
    )

def write_rtm(
    file,
    rtm_data: RtmData
) -> None:
    print(file)
    file = open(file, 'wb')
    print(file)

    # signature: char[8]
    file.write(struct.pack('8s', b'RTM_0101'))

    # absolute offset vector: float[3]
    file.write(struct.pack('3f', *rtm_data.absolute_offset))
    # nFrames: int
    file.write(struct.pack('I', len(rtm_data.frames)))
    # nBones: int
    file.write(struct.pack('I', len(rtm_data.bones)))

    def _padto32(s: bytes) -> bytes:
        assert(len(s) <= 32)
        return s + (32 - len(s)) * b'\0'

    # bones: char[32][nBones]
    for bone in rtm_data.bones:
        file.write(struct.pack('32s', _padto32(bone.encode('ascii'))))

    for frame in rtm_data.frames:
        file.write(struct.pack('f', frame.frameTime))
        for bone_transform in frame.bones:
            file.write(struct.pack('32s', _padto32(bone_transform.boneName.encode('ascii'))))
            file.write(struct.pack(
                '12f',
                *(bone_transform.transform[0] +
                bone_transform.transform[1] +
                bone_transform.transform[2] +
                bone_transform.transform[3])
            ))

def scale_rtm(
    rtm_data: RtmData,
    scale: float,
) -> RtmData:
    return RtmData(
        absolute_offset=tuple(x*scale for x in rtm_data.absolute_offset),
        bones=rtm_data.bones,
        frames=[
            RtmFrame(
                frameTime=frame.frameTime,
                bones=[
                    RtmBoneTransform(
                        boneName=bone.boneName,
                        transform=(
                            # we don't want to turn the transform itself into a
                            # scaling operation (since it'll usually only encode
                            # a rotation), just scale up the offset amount,
                            # so only scale up the translation vector
                            (bone.transform[0][0], bone.transform[0][1], bone.transform[0][2]),
                            (bone.transform[1][0], bone.transform[1][1], bone.transform[1][2]),
                            (bone.transform[2][0], bone.transform[2][1], bone.transform[2][2]),
                            (scale*bone.transform[3][0], scale*bone.transform[3][1], scale*bone.transform[3][2]),
                        )
                    )
                    for bone in frame.bones
                ]
            )
            for frame in rtm_data.frames
        ]
    )

def scale_and_rewrite_rtms(
    debinarized_path_map: dict[str, str],
    scale_factor: float
) -> dict[str, str]:
    ret: dict[str, str] = {}
    out_root_path: str = MODIFIED_RTMS_ROOT_PATH.replace('SCALE', str(scale_factor))
    for f_path in debinarized_path_map.values():
        print('scaling and writing ' + f_path)
        with open(f_path, 'rb') as infile:
            rtm_data: RtmData = read_rtm(infile)

        modified_f_path: str = out_root_path + f_path[len(DEBINARIZED_RTMS_ROOT_PATH):]

        pathlib.Path(dir_for_path(modified_f_path)).mkdir(parents=True, exist_ok=True)

        with open(modified_f_path, 'wb') as outfile:
            scaled_rtm_data = scale_rtm(rtm_data, scale_factor)
            write_rtm(outfile, scaled_rtm_data)
        ret[f_path] = modified_f_path

    return ret

def calc_or_load_modified_rtms(
    debinarized_path_map: dict[str, str],
    scale_factor: float
) -> dict[str, str]:
    SCALED_RTM_PATHS_PATH: str = "scaled_%s_rtm_paths.json" % (scale_factor,)
    if os.path.exists(SCALED_RTM_PATHS_PATH):
        try:
            with open(SCALED_RTM_PATHS_PATH, 'r') as infile:
                return json.load(infile)
        except json.decoder.JSONDecodeError:
            pass

    modified_paths: dict[str, str] = scale_and_rewrite_rtms(
        debinarized_path_map, scale_factor
    )

    with open(SCALED_RTM_PATHS_PATH, 'w') as outfile:
        json.dump(modified_paths, outfile)

    return modified_paths

def rescale_value(
    buf: str,
    value_field: str,
    scale_factor: float
) -> str:
    value_replacements: dict[str, str] = {}
    value_p = re.compile(re.escape(value_field) + r'=(-?[0-9.+e-]+);')
    for match in re.finditer(value_p, buf):
        new_value: float = float(match.group(1)) * scale_factor
        value_replacements[match.group(0)] = "%s=%s;" % (value_field, new_value,)

    for old_value, new_value in value_replacements.items():
        buf = buf.replace(old_value, new_value)
    
    return buf

def update_rtm(file_name):
    try:
        input_path = os.path.join("debinarized_rtms", file_name)
        with open(input_path, 'rb') as infile:
            stored_rtm: RtmData = read_rtm(infile)
        stored_rtm = scale_rtm(stored_rtm, SCALE)

        # Ensure the output folder exists
        output_path = os.path.join("output", file_name)
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        write_rtm(output_path, stored_rtm)
        print(f"Processed: {file_name}")
    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        traceback.print_exc()


# change working directory
script_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(script_dir)

directory = "debinarized_rtms"
processed_count = 0
error_count = 0

for root, _, files in os.walk(directory):
    for file_name in files:
        if file_name.endswith('.rtm'):
            relative_path = os.path.relpath(os.path.join(root, file_name), directory)
            try:
                update_rtm(relative_path)
                processed_count += 1
            except:
                error_count += 1

