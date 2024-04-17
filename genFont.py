import sys
import os
import json
import math
import copy
import re
from functools import reduce

sys.path.append('clsvg')
from clsvg import svgfile
from clsvg import bezierShape as bs

GLYPH_ATTRIB = {
    'version': '1.1',
    'x': '0',
    'y': '0',
    'viewBox': '0 0 1024 1024',
    'style': 'enable-background:new 0 0 1024 1024;',
    'xmlns': "http://www.w3.org/2000/svg",
    'space': 'preserve'
    }
TEMP_GLYPH_FILE = 'tempGlyph.svg'
FONT_SIZE = 1024
STROKE_WIDTH = 32
GLYPFH_WIDTH = 0.76
CHAR_WIDTH = 860
FONT_VARSION = "1.0"
DATA_FILE = "./struc_data/struc_data.json"
TEST_GLYPHS_DIR = './test_glyphs'
SYMBOLS_DIR = 'symbols'

def loadJson(file):
    with open(file, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def lineSymbol(p1, p2):
    if p1.x == p2.x:
        return 'v'
    elif p1.y == p2.y:
        return 'h'
    else:
        return 'd'
    
def getCharData(data, scale=1):
    p_map = {'h': set(), 'v': set()}
    path_list = []
    collision = {}
    for list in data['comb']["key_paths"]:
        prep = None
        path = []

        isHide = False
        for kp in list['points']:
            if kp['p_type'] == "Hide":
                isHide = True
                break
        if isHide: continue

        for kp in list['points']:
            pos = bs.Point(round(kp['point'][0] * scale), round(kp['point'][1] * scale))
            if pos != prep:
                p_map['h'].add(pos.x)
                p_map['v'].add(pos.y)
                path.append(pos)
                prep = pos
        
        if len(path) > 1:
            # head = { "symbol": lineSymbol(path[0], path[1]), "index": len(path_list)}
            # tail = { "symbol": lineSymbol(path[-1], path[-2]), "index": len(path_list)}
            # if path[0] != path[-1]:
            #     if path[0] in collision:
            #         collision[path[0]].append(head)
            #     else:
            #         collision[path[0]] = [head]

            #     if path[-1] in collision:
            #         collision[path[-1]].append(tail)
            #     else:
            #         collision[path[-1]] = [tail]

            path_list.append(path)

    map_to = {}
    for p, infos in collision.items():
        infos.sort(key=lambda x: x['symbol'], reverse=False)
        def mapToIndex(i):
            while i in map_to:
                i = map_to[i]
            return i
        while len(infos) > 1:
            oneInfo = infos.pop()
            towInfo = infos.pop()
            oneIndex = mapToIndex(oneInfo['index'])
            towIndex = mapToIndex(towInfo['index'])

            if oneIndex != towIndex:
                map_to[towIndex] = oneIndex
                if path_list[oneIndex][0] == p:
                    path_list[oneIndex].reverse()
                if path_list[towIndex][0] != p:
                    path_list[towIndex].reverse()
                path_list[oneIndex] +=  path_list[towIndex][1:]

    bpaths = []
    for i, points in enumerate(path_list):
        if i not in map_to:
            bp = bs.BezierPath()
            bp.start(points[0])
            bp.extend([bs.BezierCtrl(points[j] - points[j-1]) for j in range(1, len(points))])
            if points[0] == points[-1]:
                bp.close()
            bpaths.append(bp)

    scale = data["info"]["scale"]
    p_map['h'] = sorted(p_map['h'])
    p_map['v'] = sorted(p_map['v'])

    return scale, p_map, bpaths

def direction(pos):
    if pos.x < 0 and pos.y > 0:
        return '1'
    elif pos.x < 0 and pos.y == 0:
        return '4'
    elif pos.x < 0 and pos.y < 0:
        return '7'
    elif pos.x == 0 and pos.y > 0:
        return '2'
    elif pos.x == 0 and pos.y == 0:
        return '5'
    elif pos.x == 0 and pos.y < 0:
        return '8'
    elif pos.x > 0 and pos.y > 0:
        return '3'
    elif pos.x > 0 and pos.y == 0:
        return '6'
    elif pos.x > 0 and pos.y < 0:
        return '9'
    else:
        raise Exception("posx")
        
def strokeDirection(bpath):
    text = ''
    for ctrl in bpath:
        text += direction(ctrl.pos)

    return text

def getStrucView(bpaths, p_map):
    def map_x(v):
        return p_map['h'].index(v)
    def map_y(v):
        return p_map['v'].index(v)

    view = [[[] for n in range(len(p_map['h']))] for m in range(len(p_map['v']))]

    for i, path in enumerate(bpaths):
        start = path.startPos()
        prePos = bs.Point(map_x(start.x), map_y(start.y))
        for j, ctrl in enumerate(path):
            sym = lineSymbol(bs.Point(), ctrl.pos)
            attrs = {
                'symbol': sym,
                'indexes': [i, j],
                'padding': False,
                'dir': direction(ctrl.pos),
                'se': 0
            }
            view[prePos.y][prePos.x].append(attrs)
            start += ctrl.pos
            currPos = bs.Point(map_x(start.x), map_y(start.y))
            attrs = {
                'symbol': sym,
                'indexes': [i, j],
                'padding': False,
                'dir': direction(ctrl.pos),
                'se': 1
            }
            view[currPos.y][currPos.x].append(attrs)

            attrs = {
                'symbol': sym,
                'indexes': [i, j],
                'padding': True
            }
            if sym == 'd':
                for y in range(min(prePos.y, currPos.y)+1, max(prePos.y, currPos.y)):
                    for x in range(min(prePos.x, currPos.x)+1, max(prePos.x, currPos.x)):
                        if (y != prePos.y or x != prePos.x) and (y != currPos.y or x != currPos.x):
                            view[y][x].append(attrs)
            else:
                if sym == 'h':
                    for k in range(min(prePos.x, currPos.x) + 1, max(prePos.x, currPos.x)):
                        view[currPos.y][k].append(attrs)
                if sym == 'v':
                    for k in range(min(prePos.y, currPos.y) + 1, max(prePos.y, currPos.y)):
                        view[k][currPos.x].append(attrs)

            prePos = currPos

    return view

def strokeCtrl(pos, prePos, nectPos, unit):
    if pos.x < 0:
        if pos.y > 0:
            if prePos:
                if prePos.y > 0 and prePos.x == 0:
                    corr = prePos.y * 0.5
                    p1 = bs.Point(0, corr + pos.y * 0.3)
                    return bs.BezierCtrl(pos + bs.Point(0, corr), p1=p1), corr
                raise 'undefine'
            if nectPos:
                if nectPos.y > 0 and nectPos.x == 0:
                    corr = min(nectPos.y * 0.5, unit.y)
                    return bs.BezierCtrl(pos + bs.Point(0, corr), p2=bs.Point(pos.x, (pos.y+corr)/2))
                raise 'undefine'
            
            if abs(pos.x) < unit.x * 1.5:
                return bs.BezierCtrl(pos)
            elif abs(pos.x) < abs(pos.y):
                p1 = pos / 2
                p1.x *= abs(p1.x / p1.y)
                return bs.BezierCtrl(pos, p1=p1)
            else:
                p2 = pos / 2.4
                p2.y += (1 - abs(p2.y / p2.x)) * (pos.y - p2.y)
                return bs.BezierCtrl(pos, p2=p2)
        else:
            raise 'undefine'
    else:
        if pos.y > 0:
            if prePos and nectPos:
                if prePos.y > 0 and prePos.x == 0 and nectPos.x > 0 and nectPos.y == 0:
                    corr = prePos.y * 0.5
                    p1 = bs.Point(0, corr + pos.y * 0.3)
                    p2 = bs.Point(min(pos.x*2, (pos.x + nectPos.x)/2), pos.y + corr)
                    return bs.BezierCtrl(pos + bs.Point(nectPos.x, corr), p1=p1, p2=p2), corr
                else:
                    raise 'undefine'
            if prePos:
                if prePos.y > 0 and prePos.x == 0:
                    corr = prePos.y * 0.5
                    p1 = bs.Point(0, corr + pos.y * 0.3)
                    return bs.BezierCtrl(pos + bs.Point(0, corr), p1=p1), corr
                raise 'undefine'
            if nectPos:
                if nectPos.y > 0 and nectPos.x == 0:
                    corr = min(nectPos.y * 0.5, unit.y)
                    p1 = bs.Point(pos.x, (pos.y + corr) * 0.4)
                    return bs.BezierCtrl(pos + bs.Point(0, corr), p1=p1)
                elif nectPos.x > 0 and nectPos.y == 0:
                    return bs.BezierCtrl(pos + nectPos, p1=pos)
                raise 'undefine'
            
            if abs(pos.x) < unit.x * 1.5:
                return bs.BezierCtrl(pos)
            elif abs(pos.x) < abs(pos.y):
                p2 = pos / 2
                p2.x *= abs(p2.x / p2.y)
                return bs.BezierCtrl(pos, p2=p2)
            else:
                p2 = pos / 2
                p2.y += pos.y * (1 - abs(p2.y / p2.x)) * 0.5
                return bs.BezierCtrl(pos, p2=p2)
        else:
            raise 'undefine'

def toStrokes(bpath, strokeWidth, p_map, view, scale, npath, bpaths):
    def mapx(v): return p_map['h'].index(v)
    def mapy(v): return p_map['v'].index(v)

    def axis_value(x, y, axis, inverse):
        if axis == 'x':
            if inverse:
                return y
            else:
                return x
        else:
            if inverse:
                return x
            else:
                return y
            
    def in_view(i, j, axis):
        if axis == 'x':
            return view[i][j]
        else:
            return view[j][i]

    def extendedInfo(pos, tangent, nctrl):
        viewX = mapx(pos.x)
        viewY = mapy(pos.y)
        info = {
            'front': [],
            'back': [],
        }

        find_self = False
        for attrs in view[viewY][viewX]:
            if attrs['indexes'][0] == npath and attrs['indexes'][1] == nctrl:
                find_self = True
                continue

            if find_self:
                info['back'].append(attrs)
            else:
                info['front'].append(attrs)

        if tangent.x * tangent.y == 0:
            if tangent.x == 0:
                axis = 'y'
                if tangent.y > 0:
                    dirn = 1
                else:
                    dirn = -1
            else:
                axis = 'x'
                if tangent.x > 0:
                    dirn = 1
                else:
                    dirn = -1
            
            axis_list = p_map[axis_value('h', 'v', axis, False)]
            inaxis_list = p_map[axis_value('h', 'v', axis, True)]
            parallel_check = []

            startV1 = axis_value(viewX, viewY, axis, True)
            for advance in range(0, len(inaxis_list)):
                distance = abs(inaxis_list[startV1] - inaxis_list[advance])
                if distance <= STROKE_WIDTH / 2:
                    parallel_check.append(advance)
                elif inaxis_list[advance] > inaxis_list[startV1]:
                    break
            
            startV2 = axis_value(viewX, viewY, axis, False)
            j = startV2
            while True:
                for parVal in parallel_check:
                    if parVal == startV1 and j == startV2:
                        continue
                    for attrs in in_view(parVal, j, axis):
                        if attrs['symbol'] != 'd':# or not attrs['padding']:
                            if j == startV2 and attrs['padding']:
                                continue
                            if j == startV2 and tangent.x == 0 and tangent.y > 0:
                                continue
                            distance = abs(axis_list[startV2] - axis_list[j])
                            info['extend'] = distance
                            break
                    if 'extend' in info: break
                if 'extend' in info: break

                j += dirn
                if j < 0 or j == len(axis_list):
                    break
            
            j = startV2
            while j >= 0 and j < len(axis_list):
                for attrs in in_view(startV1, j, axis):
                    if (attrs['symbol'] == 'd' and not attrs['padding']) or attrs['indexes'] != [npath, nctrl] or (attrs['indexes'] == [npath, nctrl] and not attrs['padding']):
                        info['areaLen'] = abs(axis_list[startV2] - axis_list[j])
                        j = -2
                        break

                j -= dirn
        else:
            if tangent.y > 0:
                dirnY = 1
            else:
                dirnY = -1
            if tangent.x > 0:
                dirnX = 1
            else:
                dirnX = -1

            info['extend'] = [-1, -1]
            find = [True, True]
            y = viewY
            x = viewX
            while find[0] and find[1]:
                y += dirnY
                x += dirnX
                if y < 0 or y == len(p_map['v']):
                    find[0] = False
                    y -= dirnY
                if x < 0 or x == len(p_map['h']):
                    find[1] = False
                    x -= dirnX
                    
                if find[0]:
                    for i in range(viewY, y+1, dirnY):
                        for attrs in view[i][x]:
                            if attrs['symbol'] != 'd' or not attrs['padding']:
                                distance = abs(p_map['v'][viewY] - p_map['v'][i])
                                info['extend'][0] = distance
                                find[0] = False
                                break
                        if not find[0]: break
                if find[1]:
                    for i in range(viewX, x+1, dirnX):
                        for attrs in view[y][i]:
                            if attrs['symbol'] != 'd' or not attrs['padding']:
                                distance = abs(p_map['h'][viewX] - p_map['h'][i])
                                info['extend'][1] = distance
                                find[1] = False
                                break
                        if not find[1]: break
        
        return info

    parallelPath = [bs.BezierPath(),  bs.BezierPath()]
    pathList = []
    dirAttrs = strokeDirection(bpath) + '*'

    prePos = bpath.startPos()
    preDir = '*'
    preCtrl = None
    index = 0
    unit = bs.Point(scale['h'], scale['v']) * FONT_SIZE
    while index < len(bpath):
        dir = dirAttrs[index]
        nectDir = dirAttrs[index+1]
        ctrl = bpath[index]
        currPos = prePos + ctrl.pos

        if dir == '6':
            STROKE = {
                'length': 32,
                'h': [],
                'v': [
                    12,
                ],
                'end': {
                    'length': 64,
                    'h': [
                        24,
                    ],
                    'v': [
                        18,
                        12
                    ],
                },
                'end_2': {
                    'length': 64,
                    'h': [
                        18,
                        14
                    ],
                    'v': [
                        18,
                        34,
                        16
                    ],
                }
            }

            pathLen = ctrl.pos.x
            if preDir == '*':
                expInfo = extendedInfo(prePos, -ctrl.pos, index)

                serif = True
                other = False
                for i in range(len(expInfo['front'])):
                    attrs = expInfo['front'][i]
                    if attrs['symbol'] != 'd':
                        if 'dir' in attrs and attrs['dir'] == '2' and i < len(expInfo['front'])-1:
                            temp = expInfo['front'][i+1]
                            if temp['dir'] == '1' and attrs['indexes'][0] == temp['indexes'][0] and attrs['indexes'][1]+1 == temp['indexes'][1]:
                                expInfo['extend'] = 0
                                continue
                        serif = False
                    elif attrs['padding']:
                        inOther = False
                        for tempAttrs in expInfo['front'] + expInfo['front']:
                            if tempAttrs['symbol'] != 'd':
                                inOther = True
                                break
                        if inOther: continue

                        collPath = bpaths[attrs['indexes'][0]]
                        if len(bpaths[attrs['indexes'][0]]) > 1 and collPath[attrs['indexes'][1]].pos.y > 0:
                            if attrs['indexes'][1] > 0:
                                tempCtrl = collPath[attrs['indexes'][1]-1].pos
                                if direction(tempCtrl) == '2':
                                    collCtrl, corr = strokeCtrl(collPath[attrs['indexes'][1]].pos, tempCtrl, None, unit)
                                    collCtrlPos = collPath.posIn(attrs['indexes'][1])
                                    collCtrlPos.y -= corr
                                else:
                                    collCtrl = strokeCtrl(collPath[attrs['indexes'][1]].pos, None, None, unit)
                                    collCtrlPos = collPath.posIn(attrs['indexes'][1])
                            else:
                                raise 'undefine'
                        else:
                            collCtrl = strokeCtrl(collPath[attrs['indexes'][1]].pos, None, None, unit)
                            collCtrlPos = collPath.posIn(attrs['indexes'][1])

                        [_, t] = collCtrl.intersections(collCtrlPos, ctrl, prePos)
                        if len(t):
                            collPos = ctrl.valueAt(t[0], prePos)
                            ctrl.pos.x -= collPos.x - prePos.x
                            prePos = collPos
                            pathLen = ctrl.pos.x
                            serif = False
                        expInfo['extend'] = 0
                    else:
                        if attrs['dir'] == '1' and attrs['se'] == 0:
                            if attrs['indexes'][1] > 0 and bpaths[attrs['indexes'][0]][attrs['indexes'][1]-1].pos.x == 0:
                                continue
                            serif = False
                        elif attrs['dir'] == '1' and attrs['se'] == 1:
                            other = True
                        else:
                            raise 'undefine'
                i = 0
                while i < len(expInfo['back']):
                    attrs = expInfo['back'][i]
                    if attrs['padding']:
                        if attrs['symbol'] != 'd':
                            serif = False
                    else:
                        if 'dir' in attrs and attrs['dir'] == '2' and i < len(expInfo['back'])-1:
                            temp = expInfo['back'][i+1]
                            if temp['dir'] == '1' and attrs['indexes'][0] == temp['indexes'][0] and attrs['indexes'][1]+1 == temp['indexes'][1]:
                                expInfo['extend'] = 0
                                i += 2
                                continue
                        other = True
                    i += 1
                
                if serif:
                    expandLen = expInfo.get('extend', 9999)
                    if other:
                        if expandLen < STROKE['length']:
                            raise 'undefine'
                        expandLen = STROKE['length']
                    elif expandLen > STROKE_WIDTH * 3/2:
                        expandLen = STROKE_WIDTH / 2
                    elif expandLen > STROKE_WIDTH / 2:
                        expandLen = STROKE_WIDTH / 4
                    else:
                        expandLen = 0
                    pathLen += expandLen

                    areaLen = abs(ctrl.pos.x) / 2
                    areaLen += expandLen
                    
                    parallelPath[0].start(prePos - bs.Point(expandLen, STROKE_WIDTH / 2))
                    parallelPath[0].connect(bs.Point(pathLen, 0))
                    
                    parallelPath[1].start(prePos - bs.Point(expandLen, STROKE_WIDTH / 2))

                    if areaLen < STROKE['length']:
                        parallelPath[1].connect(bs.Point(areaLen, STROKE_WIDTH))
                        parallelPath[1].connect(bs.Point(pathLen - areaLen, 0))
                    else:
                        parallelPath[1].connect(bs.Point(0, STROKE['v'][0]))
                        parallelPath[1].connect(bs.Point(STROKE['length'], STROKE_WIDTH - STROKE['v'][0]))
                        parallelPath[1].connect(bs.Point(pathLen - STROKE['length'], 0))
                else:
                    parallelPath[0].start(prePos - bs.Point(0, STROKE_WIDTH / 2))
                    parallelPath[0].connect(bs.Point(pathLen, 0))
                    parallelPath[1].start(prePos - bs.Point(0, STROKE_WIDTH / 2))
                    parallelPath[1].connect(bs.Point(0, STROKE_WIDTH))
                    parallelPath[1].connect(bs.Point(pathLen, 0))
            elif preDir == '2' or preDir == '1':
                    parallelPath[0].connect(currPos - parallelPath[0].endPos() + bs.Point(0, -STROKE_WIDTH/2))
                    parallelPath[1].connect(currPos - parallelPath[1].endPos() + bs.Point(0, STROKE_WIDTH/2))
            else:
                raise 'undefine'
            
            if nectDir == '*':
                expInfo = extendedInfo(currPos, ctrl.pos, index)
                other = False
                serif = True
                for attrs in expInfo['front']:
                    if attrs['symbol'] != 'd':
                       serif = False
                    else:
                        expInfo['extend'] = 0
                for attrs in expInfo['back']:
                    if attrs['padding']:
                        if attrs['symbol'] != 'd':
                            serif = False
                        else:
                            inOther = False
                            for tempAttrs in expInfo['front'] + expInfo['front']:
                                if tempAttrs['symbol'] != 'd':
                                    inOther = True
                                    break
                            if inOther: continue

                            collPath = bpaths[attrs['indexes'][0]]
                            if len(bpaths[attrs['indexes'][0]]) > 1:
                                pass
                            else:
                                corrs = [0, 0]
                                collPath = bpaths[attrs['indexes'][0]]
                                tempCtrl = collPath[attrs['indexes'][1]-1].pos
                                collCtrl = strokeCtrl(tempCtrl, None, None, unit)
                                collCtrlPos = collPath.posIn(attrs['indexes'][1])

                                [collT, t] = collCtrl.intersections(collCtrlPos, ctrl, prePos)
                                if len(t):
                                    tempTangent = collCtrl.tangents(collT[0], pos=collCtrlPos)
                                    corrs[0] = bs.intersection(tempTangent[0], tempTangent[1], prePos - bs.Point(0, STROKE_WIDTH/2), currPos - bs.Point(0, STROKE_WIDTH/2,)).x - currPos.x
                                    corrs[1] = bs.intersection(tempTangent[0], tempTangent[1], prePos + bs.Point(0, STROKE_WIDTH/2), currPos + bs.Point(0, STROKE_WIDTH/2,)).x - currPos.x
                                    
                                    parallelPath[0][-1].pos.x += corrs[0]
                                    parallelPath[1][-1].pos.x += corrs[1]
                                    serif = False
                                    break
                            
                            expInfo['extend'] = 0
                    elif attrs['dir'] == '2':
                        if len(expInfo['back']) != 1:
                            raise 'undefine'
                        serif = False
                    else:
                        other = True

                if serif:
                    expandLen = expInfo.get('extend', 9999)
                    if other:
                        if expandLen < STROKE['end']['length']:
                            raise 'undefine'
                        expandLen = STROKE['end']['length']
                    elif expandLen > STROKE_WIDTH * 3/2:
                        expandLen = STROKE_WIDTH / 2
                    elif expandLen > STROKE_WIDTH / 2:
                        expandLen = STROKE_WIDTH / 4
                    else:
                        expandLen = 0

                    areaLen = abs(ctrl.pos.x) / 2
                    areaLen += expandLen
                    ratio = 1
                    if areaLen < STROKE['end']['length']:
                        ratio = areaLen / STROKE['end']['length']
                    
                    parallelPath[0][-1].pos.x += expandLen - STROKE['end']['length'] * ratio
                    parallelPath[0].connect(bs.Point(STROKE['end']['h'][0] * ratio, -STROKE['end']['v'][0]))
                    parallelPath[0].connect(bs.Point((STROKE['end']['length'] - STROKE['end']['h'][0]) * ratio, STROKE_WIDTH + STROKE['end']['v'][0] - STROKE['end']['v'][1]))
                    parallelPath[0].connect(bs.Point(0, STROKE['end']['v'][1]))
                    parallelPath[1][-1].pos.x += expandLen
                else:
                    parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                
                parallelPath[0].connectPath(parallelPath[1].reverse())
                pathList.append(parallelPath[0])
                pathList[-1].close()
            elif nectDir == '2' or nectDir == '1' or nectDir == '3':
                expInfo = extendedInfo(currPos, ctrl.pos, index)
                
                serif = True
                for attrs in expInfo['front'] + expInfo['back']:
                    if attrs['indexes'][0] != npath or (attrs['indexes'][1] != index and attrs['indexes'][1] != index + 1):
                        if not attrs['padding'] and attrs['dir'] == '2' and attrs['se'] == 1:
                            serif = False
                        elif attrs['padding'] and attrs['symbol'] == 'v':
                            serif = False
                        elif not attrs['padding'] and attrs['dir'] == '3' and attrs['se'] == 0:
                            pass # nothing
                        elif not attrs['padding'] and attrs['dir'] == '1' and attrs['se'] == 0:
                            pass # nothing
                        else:
                            raise 'undefine'

                expandLen = STROKE['end_2']['h'][1]
                
                areaLen = abs(ctrl.pos.x) / 2
                areaLen += expandLen
                ratio = 1.0
                if areaLen < STROKE['end_2']['length']:
                    ratio = areaLen / STROKE['end_2']['length']
                
                if serif:
                    parallelPath[0][-1].pos.x += STROKE_WIDTH/2 - (STROKE['end_2']['length'] - STROKE['end_2']['h'][1]) * ratio
                    parallelPath[0].connect(bs.Point(STROKE['end_2']['h'][0] * ratio, -STROKE['end_2']['v'][0] * ratio))
                    parallelPath[0].connect(bs.Point((STROKE['end_2']['length'] - STROKE['end_2']['h'][0]) * ratio, STROKE['end_2']['v'][1]))
                    parallelPath[0].connect(bs.Point(-STROKE['end_2']['h'][1] * ratio, STROKE['end_2']['v'][2]))
                    parallelPath[1][-1].pos.x -= STROKE_WIDTH / 2
                else:
                    parallelPath[0][-1].pos.x += STROKE_WIDTH/2
                    parallelPath[0].connect(bs.Point(0, STROKE_WIDTH))
                    parallelPath[1][-1].pos.x -= STROKE_WIDTH / 2
            else:
                raise Exception('Undefine stroke dir!')
        elif dir == '2':
            STROKE = {
                'length': 64,
                'h': [
                    16,
                    8,
                    8
                ],
                'v': [
                    12,
                    12
                ],
                'end': {
                    'length': 48,
                    'h': [
                        24,
                    ],
                    'v': [
                        12
                    ],
                }
            }

            pathLen = ctrl.pos.y
            if preDir == '*':
                expInfo = extendedInfo(prePos, -ctrl.pos, index)

                serif = True
                other = False
                corrs = [0, 0]
                for attrs in expInfo['front']:
                    if attrs['symbol'] != 'd':
                        serif = False
                    elif not attrs['padding']:
                        other = True
                    else:
                        inOther = False
                        for tempAttrs in expInfo['front'] + expInfo['back']:
                            if not tempAttrs['padding']:
                                inOther = True
                                break
                        if inOther: continue

                        collPath = bpaths[attrs['indexes'][0]]
                        if len(bpaths[attrs['indexes'][0]]) > 1 and collPath[attrs['indexes'][1]].pos.y > 0:
                            if attrs['indexes'][1] > 0:
                                tempCtrl = collPath[attrs['indexes'][1]-1].pos
                                if direction(tempCtrl) == '2':
                                    collCtrl, corr = strokeCtrl(collPath[attrs['indexes'][1]].pos, tempCtrl, None, unit)
                                    collCtrlPos = collPath.posIn(attrs['indexes'][1])
                                    collCtrlPos.y -= corr
                                else:
                                    collCtrl = strokeCtrl(collPath[attrs['indexes'][1]].pos, None, None, unit)
                                    collCtrlPos = collPath.posIn(attrs['indexes'][1])
                            else:
                                raise 'undefine'
                        else:
                            collCtrl = strokeCtrl(collPath[attrs['indexes'][1]].pos, None, None, unit)
                            collCtrlPos = collPath.posIn(attrs['indexes'][1])

                        [collT, t] = collCtrl.intersections(collCtrlPos, ctrl, prePos)
                        if len(t):
                            collPos = ctrl.valueAt(t[0], prePos)
                            ctrl.pos.y -= collPos.y - prePos.y
                            prePos = collPos
                            pathLen = ctrl.pos.y
                            serif = False
                            
                            tempTangent = collCtrl.tangents(collT[0], pos=collCtrlPos)
                            corrs[0] = bs.intersection(tempTangent[0], tempTangent[1], prePos + bs.Point(STROKE_WIDTH/2, 0), currPos + bs.Point(STROKE_WIDTH/2, 0)).y - prePos.y
                            corrs[1] = bs.intersection(tempTangent[0], tempTangent[1], prePos - bs.Point(STROKE_WIDTH/2, 0), currPos - bs.Point(STROKE_WIDTH/2, 0)).y - prePos.y
                        
                        expInfo['extend'] = 0
                for attrs in expInfo['back']:
                    if attrs['padding']:
                        if attrs['symbol'] != 'd':
                            serif = False
                    else:
                        other = True
                
                if serif:
                    expandLen = expInfo.get('extend', 9999)
                    if other:
                        expandTest = STROKE['length'] - STROKE_WIDTH/2
                        if expandLen < STROKE_WIDTH:
                            raise 'undefine'
                        elif expandLen < expandTest:
                            STROKE['length'] = expandLen
                        else:
                            expandLen = expandTest
                    elif expandLen > STROKE_WIDTH * 3/2:
                        expandLen = STROKE_WIDTH / 2
                    elif expandLen > STROKE_WIDTH / 2:
                        expandLen = STROKE_WIDTH / 4
                    else:
                        expandLen = 0
                    pathLen += expandLen

                    areaLen = abs(ctrl.pos.y) / 3 * 2
                    areaLen += expandLen
                    
                    if areaLen < STROKE['length']:
                        parallelPath[0].start(prePos - bs.Point(STROKE_WIDTH/2 + STROKE['h'][0], expandLen))
                        parallelPath[0].connect(bs.Point(STROKE['h'][0] + STROKE_WIDTH + STROKE['h'][2], areaLen - STROKE['v'][1]))
                        parallelPath[0].connect(bs.Point(-STROKE['h'][2], STROKE['v'][1]))
                        parallelPath[0].connect(bs.Point(0, pathLen - areaLen))
                        parallelPath[1].start(prePos - bs.Point(STROKE_WIDTH/2 + STROKE['h'][0], expandLen))
                        parallelPath[1].connect(bs.Point(STROKE['h'][0], areaLen))
                        parallelPath[1].connect(bs.Point(0, pathLen - areaLen))
                    else:
                        parallelPath[0].start(prePos - bs.Point(STROKE_WIDTH/2 + STROKE['h'][0] - STROKE['h'][1], expandLen))
                        parallelPath[0].connect(bs.Point(STROKE['h'][0] - STROKE['h'][1] + STROKE_WIDTH + STROKE['h'][2], STROKE['length'] - STROKE['v'][1]))
                        parallelPath[0].connect(bs.Point(-STROKE['h'][2], STROKE['v'][1]))
                        parallelPath[0].connect(bs.Point(0, pathLen - STROKE['length']))

                        parallelPath[1].start(prePos - bs.Point(STROKE_WIDTH/2 + STROKE['h'][0] - STROKE['h'][1], expandLen))
                        parallelPath[1].connect(bs.Point(-STROKE['h'][1], STROKE['v'][0]))
                        parallelPath[1].connect(bs.Point(STROKE['h'][0], STROKE['length'] - STROKE['v'][0]))
                        parallelPath[1].connect(bs.Point(0, pathLen - STROKE['length']))
                else:
                    parallelPath[0].start(prePos - bs.Point(STROKE_WIDTH/2, -corrs[1]))
                    parallelPath[0].connect(bs.Point(STROKE_WIDTH, corrs[0]-corrs[1]))
                    parallelPath[0].connect(bs.Point(0, pathLen+corrs[1]))
                    parallelPath[1].start(prePos - bs.Point(STROKE_WIDTH/2, -corrs[1]))
                    parallelPath[1].connect(bs.Point(0, pathLen+corrs[0]))
            elif preDir == '6' or preDir == '9' or preDir == '3' or preDir == '1':
                parallelPath[0].connect(bs.Point(0, currPos.y - parallelPath[0].endPos().y))
                parallelPath[1].connect(bs.Point(0, currPos.y - parallelPath[1].endPos().y))
            else:
                raise 'undefine'
            if nectDir == '*':
                expInfo = extendedInfo(currPos, ctrl.pos, index)
                serif = True
                other = False
                corrs = [0, 0]
                for attrs in expInfo['front']:
                    if attrs['symbol'] == 'h' and attrs['indexes'][1] > 0:
                        collPath = bpaths[attrs['indexes'][0]]
                        tempCtrl = collPath[attrs['indexes'][1]-1].pos
                        if direction(tempCtrl) == '3':
                            collCtrl = strokeCtrl(tempCtrl, None, collPath[attrs['indexes'][1]].pos, unit)
                            collCtrlPos = collPath.posIn(attrs['indexes'][1]-1)

                            [collT, t] = collCtrl.intersections(collCtrlPos, ctrl, prePos)
                            tempTangent = collCtrl.tangents(collT[0], pos=collCtrlPos)
                            corrs[0] = bs.intersection(tempTangent[0], tempTangent[1], prePos + bs.Point(STROKE_WIDTH/2, 0), currPos + bs.Point(STROKE_WIDTH/2, 0)).y - currPos.y
                            corrs[1] = bs.intersection(tempTangent[0], tempTangent[1], prePos - bs.Point(STROKE_WIDTH/2, 0), currPos - bs.Point(STROKE_WIDTH/2, 0)).y - currPos.y
                            
                            parallelPath[0][-1].pos.y += corrs[0]
                            parallelPath[1][-1].pos.y += corrs[1]
                            serif = False
                            break
                        
                    if attrs['symbol'] != 'd':
                        if not attrs['padding'] and attrs['dir'] == '6':
                            other = True
                        else:
                            serif = False
                for attrs in expInfo['back']:
                    if attrs['symbol'] == 'h' and attrs['indexes'][1] > 0:
                        collPath = bpaths[attrs['indexes'][0]]
                        tempCtrl = collPath[attrs['indexes'][1]-1].pos
                        if direction(tempCtrl) == '3':
                            collCtrl = strokeCtrl(tempCtrl, None, collPath[attrs['indexes'][1]].pos, unit)
                            collCtrlPos = collPath.posIn(attrs['indexes'][1]-1)

                            [collT, t] = collCtrl.intersections(collCtrlPos, ctrl, prePos)
                            tempTangent = collCtrl.tangents(collT[0], pos=collCtrlPos)
                            corrs[0] = bs.intersection(tempTangent[0], tempTangent[1], prePos + bs.Point(STROKE_WIDTH/2, 0), currPos + bs.Point(STROKE_WIDTH/2, 0)).y - currPos.y
                            corrs[1] = bs.intersection(tempTangent[0], tempTangent[1], prePos - bs.Point(STROKE_WIDTH/2, 0), currPos - bs.Point(STROKE_WIDTH/2, 0)).y - currPos.y
                            
                            parallelPath[0][-1].pos.y += corrs[0]
                            parallelPath[1][-1].pos.y += corrs[1]
                            serif = False
                            break
                        
                    if attrs['padding']:
                        if attrs['symbol'] != 'd':
                            serif = False
                    else:
                        other = True
                        
                if serif:
                    expandLen = expInfo.get('extend', 9999)
                    if other:
                        expandTest = STROKE['end']['length']
                        if expandLen < STROKE_WIDTH:
                            raise 'undefine'
                        elif expandLen < expandTest:
                            STROKE['end']['length'] = expandLen
                        else:
                            expandLen = expandTest
                    elif expandLen > STROKE_WIDTH * 3/2:
                        expandLen = STROKE_WIDTH / 2
                    elif expandLen > STROKE_WIDTH / 2:
                        expandLen = STROKE_WIDTH / 4
                    else:
                        expandLen = 0

                    areaLen = abs(ctrl.pos.y) / 3
                    areaLen += expandLen
                    ratio = 1
                    if areaLen < STROKE['end']['length']:
                        ratio = areaLen / STROKE['end']['length']
                    
                    parallelPath[0][-1].pos.y += expandLen - STROKE['end']['v'][0]
                    parallelPath[0].connect(bs.Point(-STROKE_WIDTH + STROKE['end']['h'][0], STROKE['end']['v'][0]))

                    parallelPath[1][-1].pos.y += expandLen - STROKE['end']['length'] * ratio
                    parallelPath[1].connect(bs.Point((STROKE['end']['h'][0]), STROKE['end']['length'] * ratio))
                else:
                    parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif nectDir == '6':
                expInfo = extendedInfo(currPos, ctrl.pos, index)
                for attrs in expInfo['front'] + expInfo['back']:
                    if attrs['indexes'][0] != npath or (attrs['indexes'][1] != index and attrs['indexes'][1] != index + 1):
                        raise 'undefine'

                if re.fullmatch(r'[^26]*268\*', dirAttrs[index:]):
                    STROKE = [
                        {
                            'h':[
                                28,
                                4
                            ],
                            'v':[
                                30,
                                24,
                                10
                            ]
                        },
                        {
                            'h':[
                                6,
                                42,
                                12
                            ],
                            'v':[
                                10
                            ]
                        },
                    ]

                    if parallelPath[0][-1].pos.y < STROKE_WIDTH/2 + STROKE[0]['v'][0]:
                        raise 'undefine'

                    index += 1
                    ctrl = bpath[index]
                    pathLen = ctrl.pos.x
                    parallelPath[0][-1].pos.y -= STROKE_WIDTH/2 + STROKE[0]['v'][0]
                    parallelPath[0].connect(bs.Point(pathLen/2-STROKE_WIDTH/2, STROKE[0]['v'][0]), bs.Point(0, STROKE[0]['v'][1]), bs.Point(STROKE[0]['h'][0], STROKE[0]['v'][0]))
                    parallelPath[1][-1].pos.y -= STROKE_WIDTH/2 + STROKE[0]['v'][0]
                    parallelPath[1].connect(bs.Point(pathLen/2+STROKE_WIDTH/2, STROKE[0]['v'][0]+STROKE_WIDTH), bs.Point(0, STROKE[0]['v'][0] + STROKE[0]['v'][2]), bs.Point(STROKE[0]['h'][1], STROKE[0]['v'][0]+STROKE_WIDTH))

                    index += 1
                    ctrl = bpath[index]
                    expInfo = extendedInfo(currPos, ctrl.pos, index).get('extend', 9999) / 2 - ctrl.pos.y
                    pathLen = [pathLen/2, min(expInfo, unit.y)]
                    parallelPath[0].connect(bs.Point(pathLen[0], -pathLen[1] + STROKE_WIDTH/2), bs.Point(pathLen[0] - STROKE_WIDTH/2, 0), bs.Point(pathLen[0] - STROKE[1]['h'][0], -STROKE[1]['v'][0]))
                    parallelPath[1].connect(bs.Point(pathLen[0], -STROKE_WIDTH/2), bs.Point(STROKE[1]['h'][1], 0), bs.Point(pathLen[0] - STROKE[1]['h'][2], 0))
                    parallelPath[1].connect(bs.Point(STROKE_WIDTH/4, -pathLen[1]), bs.Point(STROKE_WIDTH/2, -STROKE_WIDTH**2/4 / STROKE[1]['h'][2]))

                    parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                    parallelPath[0].close()
                    pathList.append(parallelPath[0])
                else:
                    parallelPath[0][-1].pos.y -= STROKE_WIDTH/2
                    parallelPath[1][-1].pos.y -= STROKE_WIDTH/4*3
                    parallelPath[1].connect(bs.Point(-STROKE_WIDTH/3 * 2, STROKE_WIDTH/2))
                    parallelPath[1].connect(bs.Point(STROKE_WIDTH/3 * 2, STROKE_WIDTH))
                    parallelPath[1].connect(bs.Point(STROKE_WIDTH/2, -STROKE_WIDTH/4))
                    # parallelPath[1].connect(currPos + bs.Point(STROKE_WIDTH/2, STROKE_WIDTH/2) - parallelPath[1].endPos())
            elif nectDir == '3' or nectDir == '1' or nectDir == '4' or nectDir == '9':
                pass # Nothing
            else:
                raise Exception('Undefine stroke dir!')
        elif dir == '1':
            STROKE = {
                'length': 42,
                'h': [
                    18
                ],
                'v': [
                    24,
                    32
                ],
                'end': {
                    'h': [
                        20,
                        16,
                        8
                    ],
                    'v': [
                        6,
                        28
                    ]
                }
            }

            indexCorr = 0
            if nectDir == '1':
                index += 1
                nectDir = dirAttrs[index+1]
                ctrl.pos += bpath[index].pos
                currPos = prePos + ctrl.pos
                indexCorr = 1

            pathLen = ctrl.pos.distance()

            if (preDir == '*' and nectDir == '*') or preDir == '*':
                areaLen = pathLen / 3
                ratio = 1
                if areaLen < STROKE['length']:
                    ratio = areaLen / STROKE['length']

                serif = True
                expInfo = extendedInfo(prePos, -ctrl.pos, index-indexCorr)
                tempCheck = [-1, -1]
                attach = {}
                for attrs in expInfo['front']:
                    if attrs['symbol'] == 'h':
                        if not attrs['padding']:
                            if attrs['dir'] == '6' and attrs['se'] == 1:
                                serif = False
                                attach['h'] = 'h'
                                attach['v'] = 'v'
                            else:
                                raise 'undefine'
                        else:
                            serif = False
                            attach['h'] = 'h'
                    elif attrs['symbol'] == 'v':
                        serif = False
                        if tempCheck[0] == attrs['indexes'][0] and tempCheck[1]+1 == attrs['indexes'][1]:
                            tempPath = bpaths[tempCheck[0]]
                            attach['d'] = bs.BezierPath()
                            attach['d'].start(tempPath.posIn(tempCheck[1]))
                            attach['d'].append(strokeCtrl(tempPath[tempCheck[1]].pos, None, tempPath[tempCheck[1]+1].pos, unit))
                        else:
                            # if not attrs['padding']:
                            #     raise 'undefine'
                            attach['v'] = 'v'
                    else:
                        if not attrs['padding']:
                            serif = False
                            if attrs['dir'] == '3' and attrs['se'] == 1:
                                tempCheck = attrs['indexes']
                for attrs in expInfo['back']:
                    if attrs['symbol'] == 'h':
                        if not attrs['padding']:
                            prePos.y -= STROKE_WIDTH/2
                            ctrl.pos.y += STROKE_WIDTH/2
                        else:
                            serif = False
                            attach['h'] = 'h'
                    elif attrs['symbol'] == 'v':
                        # if not attrs['padding']:
                        #     raise 'undefine'
                        serif = False
                        attach['v'] = 'v'
                    else:
                        if not attrs['padding']:
                            if attrs['dir'] == '3' and attrs['se'] == 0:
                                tempPath = bpaths[attrs['indexes'][0]]
                                if attrs['indexes'][1] > 0 and abs(tempPath[attrs['indexes'][1]-1].pos.x) < 0.0001:
                                    attach['d'] = bs.BezierPath()
                                    serif = False
                                    tempCtrlm, corr = strokeCtrl(tempPath[attrs['indexes'][1]].pos, tempPath[attrs['indexes'][1]-1].pos, None, unit)
                                    attach['d'].start(tempPath.posIn(attrs['indexes'][1]) - bs.Point(0, corr))
                                    attach['d'].append(tempCtrlm)
                                    del attach['v']

                                    tempDir = ctrl.pos.normalization() * STROKE_WIDTH*1.5
                                    prePos -= tempDir
                                    ctrl.pos += tempDir
                            else:
                                raise 'undefine'
                
                comp = bs.BezierPath()
                comp.start(bs.Point(0, 0))
                sCtrl = strokeCtrl(ctrl.pos, None, None, unit)
                if serif:
                    comp.connect(bs.Point(STROKE_WIDTH * 2, STROKE['v'][0] * ratio))
                    comp.connect(bs.Point(0, pathLen - STROKE['v'][0] * ratio))
                    comp.connect(bs.Point(STROKE_WIDTH / -2, 0))
                    comp.connect(bs.Point(STROKE_WIDTH * -1.5 + STROKE['h'][0], STROKE['length'] * ratio - pathLen))
                    comp.connect(bs.Point(-STROKE['h'][0], -STROKE['v'][1] * ratio))
                    comp.close()

                    tempIncr = sCtrl.tangents(0, STROKE['v'][0])[1]
                    sCtrl.pos += tempIncr
                    sCtrl.p1 += tempIncr
                    sCtrl.p2 += tempIncr
                    comp = bs.controlComp(sCtrl, comp, prePos-tempIncr, 0.75)
                    if nectDir == '*':
                        pathList.append(comp)
                    elif nectDir == '6':
                        parallelPath[0].start(comp.startPos())
                        parallelPath[0].extend(comp[:2])
                        parallelPath[0][-1] = parallelPath[0][-1].splitting(parallelPath[0][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[0].posIn(1), interval=[0,1])[0])[0]

                        parallelPath[1].start(comp.startPos())
                        comp = comp.reverse()
                        parallelPath[1].extend(comp[:3])
                        parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[1].posIn(2), interval=[0,1])[0])[0]
                        parallelPath[1].connect(bs.Point(-STROKE['end']['h'][0], STROKE['end']['v'][0]))
                        parallelPath[1].connect(bs.Point(STROKE['end']['h'][1], STROKE['end']['v'][1]))
                        parallelPath[1].connect(bs.Point(STROKE['end']['h'][2], STROKE_WIDTH - STROKE['end']['v'][1] - STROKE['end']['v'][0]))
                    elif nectDir == '3':
                        parallelPath[0].start(comp.startPos())
                        parallelPath[0].extend(comp[:2])
                        parallelPath[1].start(comp.startPos())
                        comp = comp.reverse()
                        parallelPath[1].extend(comp[:3])
                    else:
                        raise 'undefine'
                else:
                    comp.connect(bs.Point(STROKE_WIDTH/2 * 3, 0))
                    comp.connect(bs.Point(0, pathLen))
                    comp.connect(bs.Point(-STROKE_WIDTH/2, 0))
                    comp.connect(bs.Point(-STROKE_WIDTH, -pathLen))
                    comp.close()
                    
                    corrVec = ctrl.pos.normalization() * STROKE_WIDTH
                    sCtrl = strokeCtrl(ctrl.pos + corrVec, None, None, unit)
                    comp = bs.controlComp(sCtrl, comp, prePos - corrVec, 2/3)
                    tempCtrls = []
                    tempPos = []
                    if 'h' in attach or 'v' in attach:
                        tempPos.append(None)
                        tempCtrls.append(None)
                        if 'h' in attach:
                            temp = comp[1].roots(y=prePos.y, pos=comp.posIn(1), offset=0.002, interval=[0,1])
                            if len(temp):
                                tempSplit = comp[1].splitting(temp[0])
                                tempPos[0] = comp.posIn(1) + tempSplit[0].pos
                                tempCtrls[0] = tempSplit[1]
                            else:
                                tempPos[0] = comp.posIn(1)
                                tempCtrls[0] = comp[1]
                        if 'v' in attach:
                            tempSplit = comp[1].splitting(comp[1].roots(x=prePos.x, pos=comp.posIn(1), offset=0.002, interval=[0,1])[0])
                            tempPos[0] = comp.posIn(1) + tempSplit[0].pos
                            tempCtrls[0] = tempSplit[1]
                        # else:
                        #     tempCtrls.append(comp[1])
                        #     tempPos.append(comp.posIn(1))

                        if 'h' in attach:
                            tempCtrls.append(comp[3].reverse())
                            tempPos.append(comp.startPos())
                            tempSplit = tempCtrls[-1].splitting(tempCtrls[-1].roots(y=prePos.y, pos=tempPos[-1], interval=[0,1])[0])
                            tempPos[-1] += tempSplit[0].pos
                            tempCtrls[-1] = tempSplit[1].reverse()
                        else:
                            tempCtrls.append(comp[3])
                            tempPos.append(comp.posIn(0))

                        tempCtrls.append(comp[2])
                    else:
                        tempSplit = comp[1].splitting(comp[1].intersections(comp.posIn(1), attach['d'][0], attach['d'].startPos())[0][0])
                        tempPos.append(comp.posIn(1) + tempSplit[0].pos)
                        tempCtrls.append(tempSplit[1])
                        tempSplit = comp[3].splitting(comp[3].intersections(comp.posIn(3), attach['d'][0], attach['d'].startPos())[0][0])  
                        tempPos.append(comp.posIn(3) + tempSplit[0].pos)
                        tempCtrls.append(tempSplit[0])
                        tempCtrls.append(comp[2])
                    
                    comp = bs.BezierPath()
                    comp.start(tempPos[1])
                    if 'h' in attach or 'v' in attach:
                        comp.connect(prePos - tempPos[1])
                        comp.connect(tempPos[0] - prePos)
                        tempIndex = 2
                    else:
                        comp.connect(tempPos[0] - tempPos[1])
                        tempIndex = 1
                    comp.append(tempCtrls[0])
                    comp.append(tempCtrls[2])
                    comp.append(tempCtrls[1])
                    comp.close()

                    if nectDir == '*':
                        pathList.append(comp)
                    elif nectDir == '6':
                        parallelPath[0].start(comp.startPos())
                        parallelPath[0].extend(comp[:tempIndex+1])
                        parallelPath[0][-1] = parallelPath[0][-1].splitting(parallelPath[0][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[0].posIn(tempIndex), interval=[0,1])[0])[0]

                        parallelPath[1].start(comp.startPos())
                        comp = comp.reverse()
                        parallelPath[1].append(comp[0])
                        parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[1].posIn(0), interval=[0,1])[0])[0]
                        parallelPath[1].connect(bs.Point(-STROKE['end']['h'][0], STROKE['end']['v'][0]))
                        parallelPath[1].connect(bs.Point(STROKE['end']['h'][1], STROKE['end']['v'][1]))
                        parallelPath[1].connect(bs.Point(STROKE['end']['h'][2], STROKE_WIDTH - STROKE['end']['v'][1] - STROKE['end']['v'][0]))
                    else:
                        raise 'undefine'
            elif nectDir == '*':
                if preDir == '6':
                    if ctrl.pos.y < unit.y * 2.5 or -ctrl.pos.x < unit.x * 1.5:
                        parallelPath[0].connect(currPos - parallelPath[0].endPos())
                        currNormal = ctrl.normals(1, -STROKE_WIDTH/2)[0]
                        parallelPath[0].connect(currNormal)
                        currRadian = -(-ctrl.pos).radian()
                        parallelPath[1][-1].pos.x += STROKE_WIDTH/2 - STROKE_WIDTH/2/math.tan(currRadian) - STROKE_WIDTH/2/math.sin(currRadian)
                        parallelPath[1].connect(currPos + currNormal - parallelPath[1].endPos())
                    else:
                        comp = bs.BezierPath()
                        comp.start(bs.Point(0, 0))
                        comp.connect(bs.Point(0, pathLen))
                        comp.connect(bs.Point(-STROKE_WIDTH/2, 0))
                        comp.connect(bs.Point(-STROKE_WIDTH, -pathLen))
                        
                        sCtrl = strokeCtrl(ctrl.pos, None, None, unit)
                        comp = bs.controlComp(sCtrl, comp, prePos, 2/3)

                        tempSplit = comp[0].splitting(comp[0].roots(y=prePos.y+STROKE_WIDTH/2, pos=comp.startPos())[0])
                        tempPos1 = comp.startPos() + tempSplit[0].pos
                        parallelPath[0].append(tempSplit[1])
                        parallelPath[0].append(comp[1])

                        tempSplit = comp[2].splitting(comp[2].roots(y=prePos.y+STROKE_WIDTH/2, pos=comp.posIn(2))[0])
                        tempPos2 = comp.posIn(2) + tempSplit[0].pos
                        parallelPath[1][-1].pos.x -= tempPos1.x - tempPos2.x - STROKE_WIDTH
                        parallelPath[1].append(tempSplit[0].reverse())
                        
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                    parallelPath[0].close()
                    pathList.append(parallelPath[0])
                elif preDir == '2':
                    sCtrl, corr = strokeCtrl(ctrl.pos, preCtrl.pos, None, unit)
                    parallelPath[0][-1].pos.y -= corr
                    parallelPath[1][-1].pos.y -= corr
                    pathLen += corr

                    comp = bs.BezierPath()
                    comp.start(bs.Point(0, 0))
                    comp.connect(bs.Point(-STROKE_WIDTH/2, pathLen), p2=bs.Point(0, pathLen/2))
                    comp.connect(bs.Point(-STROKE_WIDTH/2, 0))
                    comp.connect(bs.Point(0, -pathLen))

                    comp = bs.controlComp(sCtrl, comp, prePos, 0.5)
                    parallelPath[0].connectPath(comp)
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                    parallelPath[0].close()
                    pathList.append(parallelPath[0])
                else:
                    raise 'undefine'
            else:
                if preDir == '6' and nectDir == '2':
                    comp = bs.BezierPath()
                    comp.start(bs.Point(0, 0))
                    comp.connect(bs.Point(0, pathLen))
                    comp.connect(bs.Point(-STROKE_WIDTH, 0))
                    comp.connect(bs.Point(0, -pathLen))
                    
                    sCtrl = strokeCtrl(ctrl.pos, None, bpath[index+1].pos, unit)
                    comp = bs.controlComp(sCtrl, comp, prePos, 0.5)

                    tempSplit = comp[0].splitting(comp[0].roots(y=prePos.y+STROKE_WIDTH/2, pos=comp.startPos())[0])
                    tempPos1 = comp.startPos() + tempSplit[0].pos
                    parallelPath[0].append(tempSplit[1])

                    tempSplit = comp[2].splitting(comp[2].roots(y=prePos.y+STROKE_WIDTH/2, pos=comp.posIn(2))[0])
                    tempPos2 = comp.posIn(2) + tempSplit[0].pos
                    parallelPath[1][-1].pos.x -= tempPos1.x - tempPos2.x - STROKE_WIDTH
                    parallelPath[1].append(tempSplit[0].reverse())
                elif preDir == '6' and nectDir == '6':
                    if ctrl.pos.y < unit.y * 2.5 or -ctrl.pos.x < unit.x * 1.5:
                        currTangent = ctrl.pos.normalization() * STROKE_WIDTH/2
                        currNormal = ctrl.normals(1, -STROKE_WIDTH/2)[0]
                        currRadian = -(-ctrl.pos).radian()

                        parallelPath[0].connect(currPos + currTangent - parallelPath[0].endPos())
                        parallelPath[1][-1].pos.x += STROKE_WIDTH/2 - STROKE_WIDTH/2/math.tan(currRadian) - STROKE_WIDTH/2/math.sin(currRadian)
                        parallelPath[1].connect(currPos + currTangent + currNormal - parallelPath[1].endPos())
                        
                        parallelPath[0][-1] = parallelPath[0][-1].splitting(parallelPath[0][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[0].endPos()-parallelPath[0][-1].pos, interval=[0,1])[0])[0]
                        parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[1].endPos()-parallelPath[1][-1].pos, interval=[0,1])[0])[0]
                        parallelPath[1].connect(bs.Point(-STROKE['end']['h'][0], STROKE['end']['v'][0]))
                        parallelPath[1].connect(bs.Point(STROKE['end']['h'][1], STROKE['end']['v'][1]))
                        parallelPath[1].connect(bs.Point(STROKE['end']['h'][2], STROKE_WIDTH - STROKE['end']['v'][1] - STROKE['end']['v'][0]))
                    else:
                        raise 'undefine'
                elif preDir == '2' and nectDir == '3':
                    sCtrl, corr = strokeCtrl(ctrl.pos, preCtrl.pos, None, unit)
                    parallelPath[0][-1].pos.y -= corr
                    parallelPath[1][-1].pos.y -= corr
                    pathLen += corr

                    comp = bs.BezierPath()
                    comp.start(bs.Point(0, 0))
                    comp.connect(bs.Point(-STROKE_WIDTH/2, pathLen), p2=bs.Point(0, pathLen/2))
                    comp.connect(bs.Point(-STROKE_WIDTH/2, 0))
                    comp.connect(bs.Point(0, -pathLen))

                    comp = bs.controlComp(sCtrl, comp, prePos, 0.5)
                    parallelPath[0].append(comp[0])
                    parallelPath[1].append(comp[2].reverse())
                elif preDir == '6' and nectDir == '3':
                    if ctrl.pos.y < unit.y * 2.5 or -ctrl.pos.x < unit.x * 1.5:
                        currTangent = ctrl.pos.normalization() * STROKE_WIDTH/2
                        currNormal = ctrl.normals(1, -STROKE_WIDTH/2)[0]
                        currRadian = -(-ctrl.pos).radian()

                        parallelPath[0].connect(currPos + currTangent - parallelPath[0].endPos())
                        parallelPath[1][-1].pos.x += STROKE_WIDTH/2 - STROKE_WIDTH/2/math.tan(currRadian) - STROKE_WIDTH/2/math.sin(currRadian)
                        parallelPath[1].connect(currPos + currTangent + currNormal - parallelPath[1].endPos())
                        
                        # parallelPath[0][-1] = parallelPath[0][-1].splitting(parallelPath[0][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[0].endPos()-parallelPath[0][-1].pos, interval=[0,1])[0])[0]
                        # parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(y=currPos.y-STROKE_WIDTH/2, pos=parallelPath[1].endPos()-parallelPath[1][-1].pos, interval=[0,1])[0])[0]
                        # parallelPath[1].connect(bs.Point(-STROKE['end']['h'][0], STROKE['end']['v'][0]))
                        # parallelPath[1].connect(bs.Point(STROKE['end']['h'][1], STROKE['end']['v'][1]))
                        # parallelPath[1].connect(bs.Point(STROKE['end']['h'][2], STROKE_WIDTH - STROKE['end']['v'][1] - STROKE['end']['v'][0]))
                    else:
                        raise 'undefine'
                else:
                    raise 'undefine'
        elif dir == '3':
            if re.fullmatch(r'36\*', dirAttrs[index:]):
                STROKE = {
                    'length': 54
                }

                pathLen = ctrl.pos.distance() + bpath[index+1].pos.x
                comp = bs.BezierPath()
                comp.start(bs.Point(0, 0))

                if preDir == '*':
                    comp.connect(bs.Point(0, pathLen - STROKE_WIDTH/2))
                    comp.connect(bs.Point(-STROKE_WIDTH/2, STROKE_WIDTH/2))
                    comp.connect(bs.Point(-STROKE_WIDTH, -STROKE['length']))
                    comp.connect(bs.Point(STROKE_WIDTH, STROKE['length'] - pathLen))
                    comp.close()
                    sCtrl = strokeCtrl(ctrl.pos, None, bpath[index+1].pos, unit)
                    pathList.append(bs.controlComp(sCtrl, comp, prePos, 2/3))
                elif preDir == '2':
                    sCtrl, corr = strokeCtrl(ctrl.pos, bpath[index-1].pos, bpath[index+1].pos, unit)
                    pathLen += corr
                    comp.connect(bs.Point(0, pathLen - STROKE_WIDTH/2))
                    comp.connect(bs.Point(-STROKE_WIDTH/2, STROKE_WIDTH/2))
                    comp.connect(bs.Point(-STROKE_WIDTH, -STROKE['length']))
                    comp.connect(bs.Point(STROKE_WIDTH/2, STROKE['length'] - pathLen))

                    parallelPath[0][-1].pos.y -= corr
                    parallelPath[1][-1].pos.y -= corr
                    comp = bs.controlComp(sCtrl, comp, prePos - bs.Point(0, corr), 2/3)

                    parallelPath[0].extend(comp)
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                    parallelPath[0].close()
                    pathList.append(parallelPath[0])
                else:
                    raise 'undefine'

                index = len(bpath)
            else:            
                STROKE = {
                    'length': 48,
                    'h': [],
                    'v': [
                        14
                    ],
                    'start_1': 
                    {
                        'h':[
                            20,
                            8
                        ],
                        'v':[
                            12,
                            16,
                            4
                        ]
                    }
                }

                def comp1():
                    comp = bs.BezierPath()
                    comp.start(bs.Point(0, 0))
                    comp.connect(bs.Point(STROKE_WIDTH / 2, 0))
                    comp.connect(bs.Point(STROKE_WIDTH, pathLen - STROKE['length'] * ratio))
                    comp.connect(bs.Point(-STROKE_WIDTH, STROKE['length'] * ratio))
                    comp.connect(bs.Point(STROKE_WIDTH * -0.5, -STROKE['v'][0]))
                    comp.close()
                    return comp

                indexCorr = 0
                if nectDir == '3':
                    index += 1
                    nectDir = dirAttrs[index+1]
                    ctrl.pos += bpath[index].pos
                    currPos = prePos + ctrl.pos
                    indexCorr = 1

                pathLen = ctrl.pos.distance()

                if preDir == '*' and nectDir == '*':
                    serif = True
                    expInfo = extendedInfo(prePos, ctrl.pos, index-indexCorr)
                    for attrs in expInfo['front']:
                        if attrs['symbol'] == 'h':
                            serif = False
                            # raise 'undefine'
                        elif attrs['symbol'] == 'v':
                            serif = False
                            # raise 'undefine'
                        else:
                            if not attrs['padding'] and attrs['dir'] == '1':
                                if attrs['indexes'][1] == 0 and attrs['se'] == 0:
                                    collCtrl = strokeCtrl(bpaths[attrs['indexes'][0]][attrs['indexes'][1]].pos, None, None, unit)
                                    pct = 12 / collCtrl.approximatedLength()
                                    corrPos = collCtrl.valueAt(collCtrl.inDistance(pct))
                                    prePos += corrPos
                                    ctrl.pos -= corrPos
                            else:
                                if not attrs['padding']:
                                    serif = False
                                    # raise 'undefine'
                    for attrs in expInfo['back']:
                        if attrs['symbol'] == 'h':
                            raise 'undefine'
                        elif attrs['symbol'] == 'v':
                            raise 'undefine'
                        else:
                            if not attrs['padding']:
                                raise 'undefine'
                    
                    areaLen = pathLen / 3
                    ratio = 1
                    if areaLen < STROKE['length']:
                        ratio = areaLen / STROKE['length']
                    sCtrl = strokeCtrl(ctrl.pos, None, None, unit)

                    comp = comp1()

                    pathList.append(bs.controlComp(sCtrl, comp, prePos, 1/3))
                elif preDir == '*':
                    if nectDir == '2':
                        sCtrl = strokeCtrl(ctrl.pos, None, bpath[index+1].pos, unit)

                        comp = bs.BezierPath()
                        comp.start(bs.Point(0, 0))
                        comp.connect(bs.Point(STROKE_WIDTH/2, 300), p2=bs.Point(STROKE_WIDTH/2, 180))
                        comp.connect(bs.Point(-STROKE_WIDTH, 0))
                        comp.connect(bs.Point(0, -300))
                        comp.close()

                        comp = bs.controlComp(sCtrl, comp, prePos, 0.5)
                        parallelPath[0].start(comp.posIn(0))
                        parallelPath[0].append(comp[0])
                        parallelPath[1].start(comp.posIn(0))
                        parallelPath[1].append(comp[3].reverse())
                        temp = comp[2].reverse()
                        parallelPath[1].append(temp)
                    else:
                        raise 'undefine'
                elif nectDir == '*':
                    if preDir == '2':
                        sCtrl, corr = strokeCtrl(ctrl.pos, preCtrl.pos, None, unit)
                        parallelPath[0][-1].pos.y -= corr
                        parallelPath[1][-1].pos.y -= corr
                        prePos.y -= corr
                        pathLen += corr

                        comp = bs.BezierPath()
                        comp.start(bs.Point(0, 0))
                        comp.connect(bs.Point(STROKE_WIDTH/2, pathLen), p2=bs.Point(0, pathLen/2))
                        comp.connect(bs.Point(STROKE_WIDTH/2, 0))
                        comp.connect(bs.Point(0, -pathLen))

                        comp = bs.controlComp(sCtrl, comp, prePos, 0.5)
                        parallelPath[0].connectPath(comp.reverse())
                    elif preDir == '1':
                        sCtrl = strokeCtrl(ctrl.pos + bs.Point(-STROKE_WIDTH/2, STROKE_WIDTH/2), None, None, unit)
                        comp = bs.controlComp(sCtrl, comp1(), prePos - bs.Point(-STROKE_WIDTH/2, STROKE_WIDTH/2), 1/3)

                        tempSplit = parallelPath[0][-1].intersections(parallelPath[0].posIn(len(parallelPath[0])-1), comp[1], comp.posIn(1))
                        parallelPath[0][-1] = parallelPath[0][-1].splitting(tempSplit[0][0])[0]
                        parallelPath[0].append(comp[1].splitting(tempSplit[1][0])[1])
                        parallelPath[0].extend(comp[2:len(comp)-1])
                        
                        parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(y=parallelPath[1][-1].pos.y-STROKE['v'][0])[0])[0]
                        parallelPath[1].connect(bs.Point(-STROKE['start_1']['h'][0], STROKE['start_1']['v'][0]))
                        parallelPath[1].connect(bs.Point(STROKE['start_1']['h'][1], STROKE['start_1']['v'][1]))
                        tempCtrl = comp[-1].reverse()
                        tempCtrls = tempCtrl.splitting(tempCtrl.roots(y=parallelPath[1].endPos().y+STROKE['start_1']['v'][2], pos=comp.startPos())[0])
                        tempPos = comp.endPos() + tempCtrls[0].pos
                        parallelPath[1].connect(tempPos - parallelPath[1].endPos())
                        parallelPath[1].append(tempCtrls[1])
                    elif preDir == '6':
                        comp = bs.BezierPath()
                        comp.start(bs.Point(0, 0))
                        comp.connect(bs.Point(0, pathLen))
                        comp.connect(bs.Point(-STROKE_WIDTH/2, 0))
                        comp.connect(bs.Point(-STROKE_WIDTH/2, -pathLen), p2=bs.Point(-STROKE_WIDTH/2, -pathLen/2))
                        
                        sCtrl = strokeCtrl(ctrl.pos, None, None, unit)
                        comp = bs.controlComp(sCtrl, comp, prePos, 0.5)

                        tempSplit = comp[0].splitting(comp[0].roots(y=prePos.y+STROKE_WIDTH/2, pos=comp.startPos())[0])
                        tempPos1 = comp.startPos() + tempSplit[0].pos
                        parallelPath[0].append(tempSplit[1])
                        parallelPath[0].append(comp[1])

                        tempSplit = comp[2].splitting(comp[2].roots(y=prePos.y+STROKE_WIDTH/2, pos=comp.posIn(2))[0])
                        tempPos2 = comp.posIn(2) + tempSplit[0].pos
                        parallelPath[1][-1].pos.x -= tempPos1.x - tempPos2.x - STROKE_WIDTH
                        parallelPath[1].append(tempSplit[0].reverse())

                        # parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                    else:
                        raise 'undefine'
                    
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                    parallelPath[0].close()
                    pathList.append(parallelPath[0])
                else:
                    if preDir == '2' and nectDir == '9':
                        sCtrl, corr = strokeCtrl(ctrl.pos, preCtrl.pos, None, unit)
                        parallelPath[0][-1].pos.y -= corr
                        parallelPath[1][-1].pos.y -= corr
                        prePos.y -= corr
                        pathLen += corr

                        comp = bs.BezierPath()
                        comp.start(bs.Point(0, 0))
                        comp.connect(bs.Point(0, pathLen))
                        comp.connect(bs.Point(-STROKE_WIDTH, 0))
                        comp.connect(bs.Point(0, -pathLen))

                        comp = bs.controlComp(sCtrl, comp, prePos, 0.5)
                        parallelPath[1].append(comp[2].reverse())
                        parallelPath[0].append(comp[0])
                    elif preDir == '1' and nectDir == '4':
                        sCtrl = strokeCtrl(ctrl.pos + bs.Point(0, STROKE_WIDTH/4), None, None, unit)
                        comp = bs.BezierPath()
                        comp.start(bs.Point(0, 0))
                        comp.connect(bs.Point(STROKE_WIDTH/2, pathLen))
                        comp.connect(bs.Point(-STROKE_WIDTH, 0))
                        comp.connect(bs.Point(0, -pathLen))
                        comp = bs.controlComp(sCtrl, comp, prePos - bs.Point(0, STROKE_WIDTH/4), 0.5)

                        tempSplit = parallelPath[0][-1].intersections(parallelPath[0].posIn(len(parallelPath[0])-1), comp[0], comp.posIn(0))
                        parallelPath[0][-1] = parallelPath[0][-1].splitting(tempSplit[0][0])[0]
                        parallelPath[0].append(comp[0].splitting(tempSplit[1][0])[1])
                        
                        parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(y=parallelPath[1][-1].pos.y-STROKE['v'][0])[0])[0]
                        parallelPath[1].connect(bs.Point(-STROKE['start_1']['h'][0], STROKE['start_1']['v'][0]))
                        parallelPath[1].connect(bs.Point(STROKE['start_1']['h'][1], STROKE['start_1']['v'][1]))
                        tempCtrl = comp[-1].reverse()
                        tempCtrls = tempCtrl.splitting(tempCtrl.roots(y=parallelPath[1].endPos().y+STROKE['start_1']['v'][2], pos=comp.startPos())[0])
                        tempPos = comp.endPos() + tempCtrls[0].pos
                        parallelPath[1].connect(tempPos - parallelPath[1].endPos())
                        parallelPath[1].append(tempCtrls[1])
                    else:
                        raise 'undefine'
        elif dir == '4':
            STROKE = {
                'length': 120,
                'h': [
                    4,
                ],
                'v': [
                    18,
                    10,
                    10
                ],
            }

            pathLen = -ctrl.pos.x
            expInfo = extendedInfo(currPos, ctrl.pos, index)
            # for attrs in expInfo['front'] + expInfo['back']:
            #     raise 'undefine'
            if pathLen > STROKE['length']:
                pathLen = STROKE['length']
            elif pathLen < STROKE['length']:
                pathLen += expInfo.get('extend', 9999) / 2
                if pathLen > STROKE['length']:
                    pathLen = STROKE['length']
                
            if preDir == '2' and nectDir == '*':
                parallelPath[0][-1].pos.y += STROKE_WIDTH/2
                parallelPath[0].connect(bs.Point(-STROKE_WIDTH/2, STROKE['v'][0]))
                parallelPath[0].connect(bs.Point(-pathLen, -STROKE['v'][0] - STROKE_WIDTH ))
                parallelPath[0].connect(bs.Point(STROKE['h'][0], -STROKE['v'][1]))
                parallelPath[0].connect(bs.Point(pathLen - STROKE['h'][0] - STROKE_WIDTH/2, STROKE_WIDTH/2 + STROKE['v'][1] - STROKE['v'][2]))
                parallelPath[1][-1].pos.y -= STROKE['v'][2]
                
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif preDir == '3' and nectDir == '*':
                parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(y=prePos.y-STROKE_WIDTH/2, pos=parallelPath[1].posIn(len(parallelPath[1])-1))[0])[0]
                parallelPath[1].connect(bs.Point(prePos.x - parallelPath[1].endPos().x - pathLen, 0))
                parallelPath[1].connect(bs.Point(0, STROKE_WIDTH/4))
                parallelPath[1].connect(prePos + bs.Point(0, STROKE_WIDTH) - parallelPath[1].endPos())

                parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            else:
                raise 'undefine'
        elif dir == '9':
            STROKE = {
                'start': [
                    {
                        'length': 64,
                        'h': [
                            36
                        ],
                        'v': [
                            8,
                            40
                        ],
                    },
                    {
                        'h': [
                            24,
                            40,
                            4,
                            16
                        ],
                        'v': [
                            6,
                            36
                        ],
                    }
                ],
                'end': {
                    'length': 64,
                    'h': [
                        18
                    ],
                    'v': [
                        34,
                        18
                    ],
                }
            }

            pathLen = ctrl.pos.distance()
            expandVec = ctrl.pos.normalization()
            if preDir == '*':
                expInfo = extendedInfo(prePos, -ctrl.pos, index)
                if len(expInfo['front']) or len(expInfo['back']):
                    raise 'undefine'
                
                pathLen += STROKE['start'][0]['h'][0]
                if True: #ctrl.pos.x > -ctrl.pos.y:
                    rotate = ctrl.pos.radian()

                    parallelPath[0].start(prePos + bs.Point(-STROKE['start'][0]['h'][0], STROKE_WIDTH/2 - STROKE['start'][0]['v'][1] - STROKE['start'][0]['v'][0]).rotate(rotate))
                    parallelPath[0].connect(bs.Point(STROKE['start'][0]['length'], STROKE['start'][0]['v'][1]+STROKE['start'][0]['v'][0]-STROKE_WIDTH).rotate(rotate))
                    parallelPath[1].start(prePos + bs.Point(-STROKE['start'][0]['h'][0], STROKE_WIDTH/2 - STROKE['start'][0]['v'][1] - STROKE['start'][0]['v'][0]).rotate(rotate))
                    parallelPath[1].connect(bs.Point(0, STROKE['start'][0]['v'][0]).rotate(rotate))
                    parallelPath[1].connect(bs.Point(STROKE['start'][0]['h'][0], STROKE['start'][0]['v'][1]).rotate(rotate))
                else:
                    if nectDir != '*':
                        raise 'undefine'
                    parallelPath[0].start(prePos + expandVec.perpendicular() * STROKE_WIDTH/2)
                    parallelPath[1].start(prePos + expandVec.perpendicular() * STROKE_WIDTH/2)
                    parallelPath[1].connect(bs.Point(-STROKE['start'][1]['h'][0], 0))
                    parallelPath[1].connect(bs.Point(0, STROKE['start'][1]['v'][0]))
                    parallelPath[1].connect(bs.Point(STROKE['start'][1]['h'][1], STROKE['start'][1]['v'][1]))
                    parallelPath[1].connect(bs.Point(STROKE['start'][1]['h'][2], 0))
                    parallelPath[1].connect(prePos - expandVec.perpendicular() * STROKE_WIDTH/2 - parallelPath[1].endPos() + bs.Point(STROKE['start'][1]['h'][3], 0))
                
                # parallelPath[1][-1].pos.y -= STROKE_WIDTH/2
                # parallelPath[1][-1].pos += parallelPath[0].endPos() - expandVec.perpendicular() * STROKE_WIDTH/2 - parallelPath[1].endPos()
            elif preDir == '3':
                tempPos = ctrl.pos.normalization().perpendicular() * STROKE_WIDTH * 1.5 + prePos
                tempSplit = parallelPath[0][-1].intersections(parallelPath[0].posIn(len(parallelPath[0])-1), bs.BezierCtrl((tempPos - currPos) * 2), currPos)
                parallelPath[0][-1] = parallelPath[0][-1].splitting(tempSplit[0][0])[0]
                parallelPath[1].connect(prePos - parallelPath[1].endPos())
            elif preDir == '2':
                tempDir = ctrl.pos.normalization()
                tempPos1 = prePos - tempDir * STROKE_WIDTH + tempDir.perpendicular() * STROKE_WIDTH
                tempPos2 = currPos - tempDir.perpendicular() * STROKE_WIDTH/4
                interPos = bs.intersection(tempPos1, tempPos2, bs.Point(prePos.x+STROKE_WIDTH/2, prePos.y), bs.Point(prePos.x+STROKE_WIDTH/2, currPos.y))
                parallelPath[0][-1].pos.y -= prePos.y - interPos.y
                interPos = bs.intersection(tempPos1, tempPos2, bs.Point(prePos.x-STROKE_WIDTH/2, prePos.y), bs.Point(prePos.x-STROKE_WIDTH/2, currPos.y))
                parallelPath[1][-1].pos.y -= prePos.y - interPos.y
                parallelPath[1].connect(tempPos1 - interPos)
                parallelPath[1].connect(tempDir.perpendicular() * STROKE_WIDTH * -1.5)
            else:
                raise 'undefine'
            
            if nectDir == '*':
                parallelPath[0].connect(currPos - parallelPath[0].endPos())
                parallelPath[1].connect(currPos + expandVec.perpendicular() * -STROKE_WIDTH/2 - parallelPath[1].endPos())

                parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif nectDir == '2':
                parallelPath[0].connect(currPos + expandVec.perpendicular() * STROKE_WIDTH/2 - parallelPath[0].endPos())
                parallelPath[1].connect(currPos + expandVec.perpendicular() * -STROKE_WIDTH/2 - parallelPath[1].endPos())
                
                backup = STROKE_WIDTH/2 / math.cos(ctrl.pos.radian())
                parallelPath[0][-1].pos -= expandVec * backup
                parallelPath[0].connect(bs.Point(STROKE_WIDTH/2, -STROKE_WIDTH/2))
                parallelPath[0].connect(bs.Point(STROKE_WIDTH/2 + STROKE['end']['h'][0], STROKE['end']['v'][0]))
                parallelPath[0].connect(bs.Point(-STROKE['end']['h'][0], STROKE['end']['v'][1]))
                
                parallelPath[1][-1].pos -= expandVec * backup
        else:
            raise Exception('Undefine stroke dir!')

        preCtrl = ctrl
        preDir = dir
        prePos = currPos
        index += 1

    return pathList

def writeTempGlyphFromShapes(shapes, fileName, tag, attrib):
    newRoot = svgfile.ET.Element(tag, attrib)
    newRoot.text = '\n'
    styleElem = svgfile.ET.Element('style', { 'type': 'text/css' })
    styleElem.text = '.st0{fill:#000000;}'
    styleElem.tail = '\n'
    newRoot.append(styleElem)

    for shape in shapes:
        newRoot.append(shape.toSvgElement({ 'class': 'st0' }))
    newTree = svgfile.ET.ElementTree(newRoot)
    newTree.write(fileName, encoding = "utf-8", xml_declaration = True)

def testChar(char):
    data = loadJson(DATA_FILE)
    scale, p_map, bpaths = getCharData(data[char], FONT_SIZE)
    view = getStrucView(bpaths, p_map)

    shapes = []
    for i, bpath in enumerate(bpaths):
        shape = bs.BezierShape()
        shape.extend(toStrokes(bpath, STROKE_WIDTH, p_map, view, scale, i, bpaths))
        shape.transform(move=bs.Point(FONT_SIZE * (1-GLYPFH_WIDTH) / 2))
        shapes.append(shape)

    writeTempGlyphFromShapes(shapes, TEMP_GLYPH_FILE, 'svg', GLYPH_ATTRIB)

def testAllChar():
    if not os.path.exists(TEST_GLYPHS_DIR):
        os.mkdir(TEST_GLYPHS_DIR)
    else:
        for f in os.listdir(TEST_GLYPHS_DIR):
            file_path = os.path.join(TEST_GLYPHS_DIR, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

    data = loadJson(DATA_FILE)
    for char, kpath in data.items():
        scale, p_map, bpaths = getCharData(kpath, FONT_SIZE)
        view = getStrucView(bpaths, p_map)

        shapes = []
        for i, bpath in enumerate(bpaths):
            shape = bs.BezierShape()
            shape.extend(toStrokes(bpath, STROKE_WIDTH, p_map, view, scale, i, bpaths))
            shape.transform(move=bs.Point(FONT_SIZE * (1-GLYPFH_WIDTH) / 2))
            shapes.append(shape)

        writeTempGlyphFromShapes(shapes, os.path.join(TEST_GLYPHS_DIR, '%s.svg' % char), 'svg', GLYPH_ATTRIB)

def corrections(list):
    import fontforge
    font = fontforge.open("YuFanXiLiu.sfd")

    num = len(list)
    count = 0
    data = loadJson(DATA_FILE)
    for name in list:
        attrs = data[name]

        char = name
        code = ord(char)
        if code < 128:
            width = int(CHAR_WIDTH / 2)
        else:
            width = CHAR_WIDTH
        
        scale, p_map, bpaths = getCharData(attrs, FONT_SIZE)
        view = getStrucView(bpaths, p_map)
        shapes = []
        for bpath in bpaths:
            shape = bs.BezierShape()
            shape.extend(toStrokes(bpath, STROKE_WIDTH, p_map, view, scale, bpaths))
            shape.transform(move=bs.Point((CHAR_WIDTH - FONT_SIZE * GLYPFH_WIDTH) / 2))
            shapes.append(shape)
            
        writeTempGlyphFromShapes(shapes, TEMP_GLYPH_FILE, 'svg', GLYPH_ATTRIB)
        glyph = font.createChar(code)
        glyph.clear()
        glyph.importOutlines(TEMP_GLYPH_FILE)
        glyph.width = width
        glyph.removeOverlap()
        
        count += 1
        print("(%d/%d)%s: import glyph '%s' %d" % (count, num, font.fontname, char, code))            
    
    # font.generate(font.fontname + ".otf")
    font.generate(font.fontname + ".ttf")
    font.save(font.fontname + ".sfd")
    font.close()

    os.remove(TEMP_GLYPH_FILE)

def importGlyphs():
    import fontforge
    font = fontforge.open("config.sfd")
    font.version = FONT_VARSION
    font.createChar(32).width = int(FONT_SIZE/2) #空格

    data = loadJson(DATA_FILE)
    errorList = {}
    num = len(data)
    count = 0
    
    for name, attrs in reversed(data.items()):
        char = name
        code = ord(char)
        if code < 128:
            width = int(CHAR_WIDTH / 2)
        else:
            width = CHAR_WIDTH
        
        count += 1
        print("(%d/%d)%s: import glyph '%s' %d" % (count, num, font.fontname, char, code))
        
        scale, p_map, bpaths = getCharData(attrs, FONT_SIZE)
        view = getStrucView(bpaths, p_map)
        shapes = []
        try:
            for i, bpath in enumerate(bpaths):
                shape = bs.BezierShape()
                shape.extend(toStrokes(bpath, STROKE_WIDTH, p_map, view, scale, i, bpaths))
                shape.transform(move=bs.Point((CHAR_WIDTH - FONT_SIZE * GLYPFH_WIDTH) / 2))
                shapes.append(shape)
        except Exception as e:
            errorList[char] = e
            print(char, e)
        
        writeTempGlyphFromShapes(shapes, TEMP_GLYPH_FILE, 'svg', GLYPH_ATTRIB)
        glyph = font.createChar(code)
        glyph.importOutlines(TEMP_GLYPH_FILE)
        glyph.width = width
        
    fileList = os.listdir(SYMBOLS_DIR)
    num = len(fileList)
    symCount = 0
    for filename in fileList:
        filePath = '%s/%s' % (SYMBOLS_DIR, filename)
        if(filename[-4:] == '.svg'):
            if(filename[:-4].isdecimal()):
                n = int(filename[:-4])
                char = chr(n)
                code = n
                width = int(float(svgfile.parse(filePath).getroot().attrib['viewBox'].split()[2]))
            else:
                continue

            symCount += 1
            print("(%d/%d)%s: import symbol glyph '%s' %d from %s" % (symCount, num, font.fontname, char, code, filename))
            
            try:
                glyph = font.createChar(code)
                glyph.importOutlines(filePath)
                glyph.width = width
            except Exception as e:
                errorList[filename] = e
                print(filename, e)

    if len(errorList):
        print("\n%d glyphs with errors!" % len(errorList))
        for name, e in errorList.items():
            print(name, e)

    font.selection.all()
    font.removeOverlap()
    
    print("\n%s: The Font has %d glyphs" % (font.fontname, count + symCount - len(errorList)))
    print("Generate font file in %s\n" % (font.fontname + ".otf"))
    
    font.generate(font.fontname + ".otf")
    # font.generate(font.fontname + ".ttf")
    font.save(font.fontname + ".sfd")
    font.close()

    os.remove(TEMP_GLYPH_FILE)

if __name__ == '__main__':
    importGlyphs()
