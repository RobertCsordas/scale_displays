#!/usr/bin/python3

import subprocess
from dataclasses import dataclass
from typing import List
import bisect
import math

INTERNAL_DISPLAY = "eDP1"
scale = 1.5

@dataclass
class Display:
    name: str
    res: List[int]
    pos: List[int]
    scaled: False

def run(cmd: str) -> List[str]:
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    assert res.returncode == 0
    res = res.stdout.decode()
    res = [s.strip() for s in res.split("\n")]
    res = [r for r in res if r]
    return res

def find_connected_displays() -> List[List[List[str]]]:
    lines = run("xrandr")
    lines = [l.split(" ") for l in lines]
    prev_pos = -1
    res = []
    for i, l in enumerate(lines):
        if len(l)>=3 and l[1]=="connected":
            if prev_pos>=0:
                res.append(lines[prev_pos:i])
            prev_pos = i

    if prev_pos>=0 and prev_pos<len(lines)-1:
        res.append(lines[prev_pos:])    
    
    return res

def find_enabled_displays() -> List[Display]:
    displays = find_connected_displays()
    out = []
    for d in displays:    
        res = d[0][3] if d[0][2]=="primary" and len(d[0])>=4 else d[0][2]
        res = res.split("+")
        if len(res) != 3:
            continue

        pos = [int(a) for a in res[1:]]
        res = [int(a) for a in res[0].split("x")]

        reslist = [a[0] for a in d[1:]]
        res_str = f"{res[0]}x{res[1]}"

        out.append(Display(d[0][0], res, pos, res_str not in reslist))
    
    return out

def get_scale(display: str):
    if display == INTERNAL_DISPLAY:
        return 1
    else:
        return scale
    
def calculate_new_pos_in_dim(displays: List[Display], dim: int):
    def get_end_pos(d: Display) -> int:
         return d.pos[dim] + d.res[dim]

    disp_by_name = {d.name: d for d in displays}
    end_order = list(sorted([d.name for d in displays], 
                key = lambda x: get_end_pos(disp_by_name[x])))

                
    end_pos = [get_end_pos(disp_by_name[x]) for x in end_order]
    # displays = list(sorted(displays, key = lambda x: x.pos[dim]))

    def scale(name: str):
        disp = disp_by_name[name]
        if disp.scaled:
            return

        this_pos = bisect.bisect_left(end_pos, disp.pos[dim])
        while this_pos < len(end_pos) and end_pos[this_pos] == disp.pos[dim]:
            this_pos += 1
        if this_pos>0:
            prev_name = end_order[this_pos-1]
            scale(prev_name)
            d_from_prev = disp.pos[dim] - end_pos[this_pos-1]
            new_end_of_prev = disp_by_name[prev_name].pos[dim] + disp_by_name[prev_name].res[dim] * get_scale(prev_name)

            disp.pos[dim] = int(math.ceil(new_end_of_prev + d_from_prev))

        disp.scaled = True


    for d in end_order:
        scale(d)
        
    
def calculate_new_pos(displays: List[Display]):
    calculate_new_pos_in_dim(displays, 0)
    calculate_new_pos_in_dim(displays, 1)

def create_command(displays: List[Display]) -> str:
    res = "xrandr "
    for d in displays:
        scale = get_scale(d.name)
        res += f"--output {d.name} --scale {scale}x{scale} --pos {d.pos[0]}x{d.pos[1]} "
    return res

displays = find_enabled_displays()
if all([d.scaled for d in displays]):
    print("All displays scaled. Nothing to do.")
else:
    calculate_new_pos(displays)
    cmd = create_command(displays)
    run(cmd)
    subprocess.run("killall plasmashell", shell=True)
    subprocess.run("kstart5 plasmashell", shell=True)
    subprocess.run("qdbus org.kde.KWin /Compositor suspend")


