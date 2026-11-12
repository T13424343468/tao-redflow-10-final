#!/usr/bin/env python3
# 代理渲染器：镜像 Unity 沙盘的同款几何/配色/布光，用于画面自检打分（非真机画面）
import math, random, os
from PIL import Image

W, H = 960, 600
ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = f'{ROOT}/IronCommand/unity/Resources/IronTextures'

def load_photo(name):
    p = f'{PHOTO_DIR}/{name}.jpg'
    return Image.open(p).convert('RGB') if os.path.exists(p) else None

GROUND_PHOTO = load_photo('dry_ground')   # 实拍干土
SAND_PHOTO = load_photo('coast_sand')     # 实拍沙滩

# ---- 几何工具 ----
def hull_mesh(stations, color):
    """沿 z 轴放样的梯形截面壳体，stations: [(z, w, h, y), ...]"""
    tris = []
    rings = []
    for (z, w, h, y) in stations:
        rings.append([( w,      y - h,      z),
                      ( w*0.62, y + h*0.45, z),
                      ( w*0.40, y + h,      z),
                      (-w*0.40, y + h,      z),
                      (-w*0.62, y + h*0.45, z),
                      (-w,      y - h,      z)])
    for s in range(len(rings)-1):
        for i in range(6):
            j = (i+1) % 6
            tris.append((rings[s][i], rings[s][j], rings[s+1][j], color))
            tris.append((rings[s][i], rings[s+1][j], rings[s+1][i], color))
    return tris

def ellipse_mesh(stations, color, segs=10):
    tris = []
    rings = []
    for (z, w, h, y) in stations:
        ring = [(math.cos(a)*w, y + math.sin(a)*h, z) for a in
                [k*math.pi*2/segs for k in range(segs)]]
        rings.append(ring)
    for s in range(len(rings)-1):
        for i in range(segs):
            j = (i+1) % segs
            tris.append((rings[s][i], rings[s][j], rings[s+1][j], color))
            tris.append((rings[s][i], rings[s+1][j], rings[s+1][i], color))
    return tris

def bevel_box(cx, cy, cz, w, h, d, bev, color):
    hw, hh, hd = w/2, h/2, d/2
    bw, bh = min(bev, hw*0.9), min(bev, hh*0.9)
    prof = [(-hw+bw,-hh),(hw-bw,-hh),(hw,-hh+bh),(hw,hh-bh),
            (hw-bw,hh),(-hw+bw,hh),(-hw,hh-bh),(-hw,-hh+bh)]
    tris = []
    a = [(x, y, -hd) for (x, y) in prof]
    b = [(x, y,  hd) for (x, y) in prof]
    for i in range(8):
        j = (i+1) % 8
        tris.append((a[i], a[j], b[j], color))
        tris.append((a[i], b[j], b[i], color))
    tris.append((a[0], a[1], a[2], color)); tris.append((a[0], a[2], a[3], color))
    tris.append((a[0], a[3], a[4], color)); tris.append((a[0], a[4], a[5], color))
    tris.append((a[0], a[5], a[6], color)); tris.append((a[0], a[6], a[7], color))
    return [((p0[0]+cx, p0[1]+cy, p0[2]+cz), (p1[0]+cx, p1[1]+cy, p1[2]+cz),
             (p2[0]+cx, p2[1]+cy, p2[2]+cz), color) for (p0, p1, p2, color) in tris]

def cone(cx, cy, cz, radius, height, color, segs=8, tilt=0.0):
    bottom = [(cx + math.cos(k*math.pi*2/segs)*radius, cy,
               cz + math.sin(k*math.pi*2/segs)*radius) for k in range(segs)]
    tip = (cx + tilt*height, cy + height, cz)
    return [(bottom[i], tip, bottom[(i+1) % segs], color) for i in range(segs)]

# ---- 场景组装（配色/尺寸与 C# 侧一致）----
BLUE = (0x4A, 0x6F, 0xA5); RED = (0xA5, 0x3C, 0x3C)
DARK = (0x2A, 0x2C, 0x2E); GOLD = (0xC8, 0xA0, 0x28)
DIRT1 = (0x8A, 0x76, 0x58); DIRT2 = (0x7A, 0x66, 0x4A)
WATER = (0x2E, 0x5E, 0x8C); LEAF = (0x4E, 0x66, 0x34)
TRUNK = (0x5A, 0x42, 0x2E); ROCK = (0x7E, 0x76, 0x6A)

def tank_hull(yaw):
    st = [(-0.72,0.36,0.16,0.34),(-0.40,0.44,0.20,0.32),(0.20,0.46,0.22,0.30),
          (0.62,0.40,0.14,0.36),(0.75,0.26,0.10,0.40)]
    rot = [(s[0]*math.cos(yaw)-s[2]*math.sin(yaw), s[1], s[2], s[3]) for s in st]
    return [(z, w, h, y) for (z, w, h, y) in rot]

def track_mesh(yaw):
    """坦克两侧履带 + 舱口，局部坐标随车体偏航旋转"""
    out = []
    for sx in (-0.52, 0.52):
        out += bevel_box(sx, 0.17, 0.0, 0.18, 0.24, 1.95, 0.04, (0x22,0x24,0x26))
        # 履带板横纹
        for i in range(6):
            out += bevel_box(sx, 0.06, -0.78 + i*0.31, 0.20, 0.06, 0.08, 0.01, (0x1C,0x1E,0x20))
    out += bevel_box(0.0, 0.56, -0.05, 0.46, 0.10, 0.55, 0.03, (0x20,0x28,0x3A))  # 舱口盖
    out += bevel_box(0.0, 0.56, 0.45, 0.24, 0.09, 0.26, 0.02, (0x1E,0x24,0x30))   # 观察舱
    ca, sa = math.cos(yaw), math.sin(yaw)
    rot = []
    for (p0, p1, p2, c) in out:
        r0 = (p0[0]*ca - p0[2]*sa, p0[1], p0[0]*sa + p0[2]*ca)
        r1 = (p1[0]*ca - p1[2]*sa, p1[1], p1[0]*sa + p1[2]*ca)
        r2 = (p2[0]*ca - p2[2]*sa, p2[1], p2[0]*sa + p2[2]*ca)
        rot.append((r0, r1, r2, c))
    return rot

# 自然曲折海岸线：主岛与大陆边界随噪声起伏，地面网格与逐像素渲染共用同一组函数
def isl_x0(z): return 7.5 + 1.5*math.sin(z*0.23+1.2) + 0.8*math.sin(z*0.57+0.4)
def isl_x1(z): return 46.0 - 1.3*math.sin(z*0.27+2.0) - 0.7*math.sin(z*0.61+1.1)
def isl_z0(x): return 3.2 + 1.1*math.sin(x*0.29+0.7) + 0.6*math.sin(x*0.67+2.4)
def isl_z1(x): return 36.8 - 1.1*math.sin(x*0.25+1.9) - 0.6*math.sin(x*0.53+0.3)
def main_x(z): return 52.0 + 1.2*math.sin(z*0.33+0.9) + 0.6*math.sin(z*0.71+2.0)
# 四周小岛：(中心x, 中心z, 长轴, 短轴)，全部落在海面区，避开已有单位
ISLETS = [(3.5, 22.0, 1.8, 1.3), (4.5, 30.5, 1.2, 0.9),
          (17.5, 1.3, 1.6, 0.9), (20.0, 38.3, 2.0, 1.2),
          (36.5, 38.4, 1.5, 1.0), (48.5, 27.0, 1.2, 0.9)]
def islet_e(x, z):
    e = 9.9
    for (cx, cz, rx, ry) in ISLETS:
        v = ((x-cx)/rx)**2 + ((z-cz)/ry)**2
        n = 0.22*math.sin(x*1.7+cx*2.3) + 0.22*math.sin(z*1.9+cz*1.7)
        e = min(e, v + n)
    return e

def build_scene():
    tris = []
    # 全场景共用随机源：兵人/装备色差与滩头杂物同源，先建后用
    dr = random.Random(880166)
    # 地面：1m 平铺按世界坐标采样实拍照片（块内 6x6 像素均值，缺失回退棋盘）
    rj = random.Random(20241104)
    gp_img = GROUND_PHOTO.load() if GROUND_PHOTO is not None else None
    gw, gh = GROUND_PHOTO.size if GROUND_PHOTO is not None else (0, 0)
    sp_img = SAND_PHOTO.load() if SAND_PHOTO is not None else None
    sw, sh = SAND_PHOTO.size if SAND_PHOTO is not None else (0, 0)

    def patch_avg(px_img, u, v, pw, ph):
        rs = gs = bs = n = 0
        for du in range(6):
            for dv in range(6):
                uu, vv = min(pw-1, u+du), min(ph-1, v+dv)
                c = px_img[uu, vv]
                rs += c[0]; gs += c[1]; bs += c[2]; n += 1
        return (rs//n, gs//n, bs//n)

    # 隔海对峙：蓝方海岛（西），红方大陆（东），中间一道海峡
    ISL = (7.5, 46.0, 3.2, 36.8)
    MAIN_X = 52.0
    def terr(x, z):
        ie = islet_e(x, z)
        if ie < 1.0: return 'land'
        if ie < 1.5: return 'beach'
        if x < isl_x0(z): return 'water'
        if isl_x1(z) < x < main_x(z): return 'water'
        if x <= isl_x1(z):
            if z < isl_z0(x) or z > isl_z1(x): return 'water'
            d = min(x-isl_x0(z), isl_x1(z)-x, z-isl_z0(x), isl_z1(x)-z)
            return 'beach' if d < 2.2 else 'land'
        return 'beach' if (x - main_x(z)) < 2.2 else 'land'
    for gx in range(60):
        for gz in range(40):
            cx, cz = gx + 0.5, gz + 0.5
            x0, z0 = gx, gz
            tk = terr(cx, cz)
            if tk == 'water':
                # 近海：流动水面 + 阳光碎金
                j = rj.uniform(0.90, 1.08)
                if rj.random() < 0.08:
                    j *= 1.5
                c = tuple(min(255, int(q*j)) for q in WATER)
                tris.append(((x0,0.03,z0),(x0+1,0.03,z0),(x0+1,0.03,z0+1), c, 'water'))
                tris.append(((x0,0.03,z0),(x0+1,0.03,z0+1),(x0,0.03,z0+1), c, 'water'))
                continue
            if tk == 'beach' and sp_img is not None:
                # 岸缘沙滩带
                u = min(sw-7, int((cx % 9.0)/9.0*sw)); v = min(sh-7, int((cz % 9.0)/9.0*sh))
                c = patch_avg(sp_img, u, v, sw, sh)
            elif gp_img is not None:
                u = min(gw-7, int(cx/60*gw)); v = min(gh-7, int(cz/40*gh))
                c = patch_avg(gp_img, u, v, gw, gh)
            else:
                c = DIRT1 if (gx+gz) % 2 == 0 else DIRT2
            j = rj.uniform(0.96, 1.04)
            c = tuple(min(255, int(q*j)) for q in c)
            tris.append(((x0,0,z0),(x0+1,0,z0),(x0+1,0,z0+1), c, 'ground'))
            tris.append(((x0,0,z0),(x0+1,0,z0+1),(x0,0,z0+1), c, 'ground'))
    # 矿床（内迁至岛腹，远离海岸）
    for i in range(14):
        ox, oz = 16 + (i % 5) * 1.5, 4.5 + (i // 5) * 1.5
        tris += cone(ox, 0.02, oz, 0.9, 0.5, GOLD, segs=6)
    # 蓝方：基地 + 电厂 + 坦克x2 + 矿车 + 直升机 + 舰艇（全部内迁上岸）
    for (bx, bz) in [(11.0, 3.5)]:
        tris += bevel_box(bx, 0.55, bz, 3.8, 1.1, 3.8, 0.12, BLUE)
        tris += bevel_box(bx, 1.24, bz, 3.6, 0.32, 3.6, 0.14, (0x3A,0x54,0x7E))
    tris += bevel_box(10.5, 0.35, 7.5, 1.6, 0.7, 2.2, 0.1, BLUE)   # 工厂
    for (tx, tz, yaw) in [(13.0, 3.4, 0.0), (14.5, 5.0, 0.35)]:
        m = hull_mesh(tank_hull(yaw), BLUE)
        tris += [((p0[0]+tx, p0[1], p0[2]+tz), (p1[0]+tx, p1[1], p1[2]+tz),
                  (p2[0]+tx, p2[1], p2[2]+tz), c) for (p0, p1, p2, c) in m]
        tm = track_mesh(yaw)
        tris += [((p0[0]+tx, p0[1], p0[2]+tz), (p1[0]+tx, p1[1], p1[2]+tz),
                  (p2[0]+tx, p2[1], p2[2]+tz), c) for (p0, p1, p2, c) in tm]
        tris += cone(tx, 0.6, tz+0.4, 0.12, 1.1, DARK, segs=6, tilt=-0.18)  # 炮管
    # 矿车（斜面斗，靠矿场停放）
    tris += cone(17.0, 0.1, 10.2, 0.55, 0.5, GOLD, segs=5)
    tris += bevel_box(17.0, 0.45, 10.2, 1.2, 0.55, 0.9, 0.08, BLUE)
    # 直升机（椭圆机身 + 尾梁 + 旋翼盘）
    tris += ellipse_mesh([(0.0,0.26,0.21,2.25),(0.5,0.18,0.15,2.23),(0.8,0.05,0.05,2.2)], BLUE)
    tris += [((14.2,2.3,6.7),(14.9,2.3,6.7),(14.9,2.32,6.75), BLUE),
             ((14.2,2.3,6.7),(14.9,2.32,6.75),(14.2,2.32,6.75), BLUE)]
    tris += cone(14.5, 2.55, 6.72, 0.9, 0.06, DARK, segs=4)
    # 舰艇
    for (sx, sz) in [(3.0, 13.5)]:
        st = [(-1.0,0.30,0.12,0.24),(-0.4,0.34,0.15,0.26),(0.4,0.30,0.14,0.26),
              (0.86,0.14,0.08,0.28),(1.0,0.04,0.05,0.30)]
        m = hull_mesh(st, BLUE)
        tris += [((p0[0]+sx, p0[1], p0[2]+sz), (p1[0]+sx, p1[1], p1[2]+sz),
                  (p2[0]+sx, p2[1], p2[2]+sz), c) for (p0, p1, p2, c) in m]
    # 红方：基地 + 工厂 + 坦克x2（内迁上岸）
    tris += bevel_box(53.5, 0.55, 6.0, 3.8, 1.1, 3.8, 0.12, RED)
    tris += bevel_box(54.5, 0.35, 9.5, 1.6, 0.7, 2.2, 0.1, RED)
    for (tx, tz) in [(52.0, 4.0), (53.5, 6.5)]:
        m = hull_mesh(tank_hull(3.14), RED)
        tris += [((p0[0]+tx, p0[1], p0[2]+tz), (p1[0]+tx, p1[1], p1[2]+tz),
                  (p2[0]+tx, p2[1], p2[2]+tz), c) for (p0, p1, p2, c) in m]
        tm = track_mesh(3.14)
        tris += [((p0[0]+tx, p0[1], p0[2]+tz), (p1[0]+tx, p1[1], p1[2]+tz),
                  (p2[0]+tx, p2[1], p2[2]+tz), c) for (p0, p1, p2, c) in tm]
        tris += cone(tx, 0.6, tz-0.4, 0.12, 1.1, DARK, segs=6, tilt=-0.18)

    # ---- 本轮新单位（镜像 DemoTankFactory 新模型）----
    def _camo_patch_col():
        # 迷彩斑块取色：每人从三色族独立抽两色组合，同队不重样
        fam = ((0x2E,0x3A,0x28),(0x4E,0x4A,0x34),(0x6E,0x6C,0x55))
        c1 = fam[dr.randrange(3)]
        c2 = fam[(fam.index(c1) + 1 + dr.randrange(2)) % 3]
        return (c1, c2)
    def soldier(x, z, col, pose='stand', yaw=0.0):
        # 威龙风格兵人：分腿/战术背心挂具/弹匣袋/背包/完整步枪，pose 可选 stand/kneel/sit/prone
        # 逐人差异：漆面/装具/肤色明度抖动，约三成轻装不背背包
        j = dr.uniform(-0.10, 0.10)
        tint = lambda c: tuple(min(255, max(0, int(c[i]*(1.0+j)))) for i in range(3))
        dark  = tint((0x2A, 0x2C, 0x2E))
        gear  = tint((0x3E, 0x44, 0x3A))
        skin  = tint((0x8E, 0x6E, 0x52))
        col   = tint(col)
        light = dr.random() < 0.3
        if pose == 'prone':
            # 伏地姿态：躯干贴地水平、双腿后伸、枪口朝前，供掩体后/滩头火力位
            parts  = bevel_box(x, 0.10, z+0.02, 0.15, 0.075, 0.30, 0.02, col)      # 躯干（水平）
            parts += bevel_box(x, 0.155, z+0.02, 0.13, 0.055, 0.20, 0.012, gear)   # 背心（背上）
            parts += bevel_box(x-0.035, 0.05, z-0.26, 0.05, 0.055, 0.34, 0.012, dark)  # 左腿后伸
            parts += bevel_box(x+0.035, 0.05, z-0.26, 0.05, 0.055, 0.34, 0.012, dark)  # 右腿后伸
            parts += cone(x, 0.155, z+0.20, 0.062, 0.075, col, segs=6)             # 头盔在前
            parts += bevel_box(x, 0.105, z+0.255, 0.07, 0.042, 0.045, 0.008, skin) # 脸部
            parts += bevel_box(x+0.05, 0.085, z+0.32, 0.03, 0.042, 0.28, 0.008, dark)  # 枪前伸
            # 迷彩斑块（伏地姿态：背心+躯干面）
            camo = _camo_patch_col()
            parts += bevel_box(x-0.03, 0.185, z-0.02, 0.06, 0.012, 0.09, 0.003, camo[0])
            parts += bevel_box(x+0.04, 0.185, z+0.08, 0.05, 0.012, 0.07, 0.003, camo[1])
            parts += bevel_box(x-0.076, 0.12, z+0.05, 0.012, 0.05, 0.10, 0.003, camo[1])
            if abs(yaw) > 0.01:
                ca, sa = math.cos(yaw), math.sin(yaw)
                rot = []
                for (p0, p1, p2, c) in parts:
                    rr = []
                    for p in (p0, p1, p2):
                        dx, dz = p[0]-x, p[2]-z
                        rr.append((x + dx*ca - dz*sa, p[1], z + dx*sa + dz*ca))
                    rot.append((rr[0], rr[1], rr[2], c))
                parts = rot
            tris.extend(parts)
            return
        if pose == 'sit':
            leg_h = 0.16
        elif pose == 'kneel':
            leg_h = 0.27
        else:
            leg_h = 0.42
        torso_y = leg_h + 0.095
        if pose == 'sit':
            # 坐姿：双腿前伸贴地，躯干放低
            parts  = bevel_box(x-0.045, 0.05, z+0.10, 0.06, 0.09, 0.17, 0.013, dark)  # 左腿前伸
            parts += bevel_box(x+0.045, 0.05, z+0.10, 0.06, 0.09, 0.17, 0.013, dark)  # 右腿前伸
        else:
            parts  = bevel_box(x-0.05, leg_h/2, z, 0.066, leg_h, 0.09, 0.013, dark)  # 左腿
            parts += bevel_box(x+0.05, leg_h/2, z, 0.066, leg_h, 0.09, 0.013, dark)  # 右腿
        parts += bevel_box(x, torso_y, z, 0.185, 0.28, 0.125, 0.028, col)          # 躯干
        parts += bevel_box(x, torso_y+0.015, z+0.058, 0.165, 0.24, 0.055, 0.018, gear) # 战术背心
        parts += bevel_box(x-0.05, torso_y-0.02, z+0.092, 0.045, 0.085, 0.048, 0.01, gear) # 弹匣袋×2
        # 装具层次补核：腰带 + 侧挂水壶 + 胸前枪带，与背心/弹匣袋凑足四层
        parts += bevel_box(x, torso_y-0.115, z, 0.19, 0.03, 0.135, 0.008, gear)           # 腰带
        parts += bevel_box(x-0.105, torso_y-0.125, z+0.02, 0.035, 0.06, 0.05, 0.008, dark) # 左腰水壶
        parts += bevel_box(x+0.055, torso_y+0.02, z+0.077, 0.014, 0.22, 0.012, 0.005, dark) # 胸前枪带
        parts += bevel_box(x+0.05, torso_y-0.02, z+0.092, 0.045, 0.085, 0.048, 0.01, gear)
        # 迷彩斑块：每人独立取色组合，躯干前后侧面随机铺，同队不重样
        camo = _camo_patch_col()
        parts += bevel_box(x-0.045, torso_y+0.06, z+0.068, 0.07, 0.10, 0.012, 0.003, camo[0])
        parts += bevel_box(x+0.055, torso_y-0.05, z+0.068, 0.06, 0.09, 0.012, 0.003, camo[1])
        parts += bevel_box(x-0.093, torso_y+0.02, z-0.01, 0.012, 0.12, 0.09, 0.003, camo[1])
        parts += bevel_box(x+0.093, torso_y+0.08, z, 0.012, 0.10, 0.08, 0.003, camo[0])
        if not light:
            parts += bevel_box(x, torso_y+0.025, z-0.082, 0.165, 0.20, 0.065, 0.018, gear)  # 背包
            parts += bevel_box(x, torso_y+0.025, z-0.115, 0.09, 0.08, 0.012, 0.003, camo[0]) # 背包迷彩盖
        parts += cone(x, torso_y+0.175, z, 0.066, 0.082, col, segs=6)              # 头盔
        parts += bevel_box(x+0.015, torso_y+0.205, z+0.008, 0.045, 0.012, 0.055, 0.003, camo[1]) # 盔顶迷彩
        parts += bevel_box(x, torso_y+0.132, z+0.052, 0.075, 0.045, 0.048, 0.008, skin) # 脸部
        ry = torso_y - 0.055
        parts += bevel_box(x+0.042, ry, z+0.14, 0.032, 0.048, 0.33, 0.008, dark)    # 枪身
        parts += bevel_box(x+0.042, ry-0.045, z+0.085, 0.028, 0.088, 0.052, 0.01, dark) # 弹匣
        parts += bevel_box(x+0.042, ry, z+0.325, 0.022, 0.022, 0.15, 0.005, dark)  # 枪管
        parts += bevel_box(x+0.042, ry-0.014, z-0.032, 0.028, 0.082, 0.078, 0.01, dark) # 枪托
        if abs(yaw) > 0.01:
            ca, sa = math.cos(yaw), math.sin(yaw)
            rot = []
            for (p0, p1, p2, c) in parts:
                rr = []
                for p in (p0, p1, p2):
                    dx, dz = p[0]-x, p[2]-z
                    rr.append((x + dx*ca - dz*sa, p[1], z + dx*sa + dz*ca))
                rot.append((rr[0], rr[1], rr[2], c))
            parts = rot
        tris.extend(parts)
    # 三三制战斗小组：班长居前，两翼展开；姿态按组传入，同屏至少三姿且同类不相邻
    def fireteam(cx, cz, col, yaw=0.0, poses=None):
        ps = poses or ('stand', 'kneel', 'stand')
        soldier(cx, cz, col, ps[0], yaw)
        soldier(cx-0.6, cz+0.55, col, ps[1], yaw+0.25)
        soldier(cx+0.6, cz+0.55, col, ps[2], yaw-0.25)
    # 蓝方步兵排：三个战斗小组呈前三角，站/跪/伏/坐四姿混编
    fireteam(5.6, 5.6, BLUE, 0.15, ('stand', 'kneel', 'prone'))
    fireteam(7.1, 6.7, BLUE, -0.1, ('prone', 'stand', 'kneel'))
    fireteam(5.8, 7.5, BLUE, 0.0, ('kneel', 'sit', 'stand'))
    # 红方步兵排：同建制对向展开，姿态对等混编
    fireteam(51.2, 5.2, RED, 3.0, ('stand', 'prone', 'kneel'))
    fireteam(52.7, 6.1, RED, 3.25, ('kneel', 'stand', 'sit'))
    fireteam(51.5, 7.0, RED, 2.9, ('sit', 'kneel', 'prone'))
    # 蓝方牵引榴弹炮：炮架+防盾+高仰角炮管
    tris += bevel_box(7.8, 0.2, 6.8, 0.5, 0.3, 1.3, 0.04, BLUE)
    tris += cone(7.8, 0.55, 7.1, 0.05, 1.1, DARK, segs=6, tilt=0.45)
    tris += bevel_box(7.8, 0.44, 6.55, 0.78, 0.55, 0.07, 0.03, BLUE)   # 防盾
    # 蓝方轮式突击车
    tris += bevel_box(4.2, 0.4, 7.6, 0.92, 0.38, 1.75, 0.07, BLUE)
    tris += cone(4.2, 0.64, 7.5, 0.13, 0.16, BLUE, segs=6)
    # 蓝方两栖战车（水际线）
    tris += bevel_box(4.6, 0.2, 11.2, 0.6, 0.34, 1.5, 0.08, BLUE)
    # 蓝方喷气战机（空中）
    tris += ellipse_mesh([(0.0,0.16,0.12,3.1),(0.5,0.18,0.14,3.1),(1.1,0.05,0.05,3.1)], BLUE)
    tris += [((9.2,3.05,8.4),(10.6,3.05,8.4),(10.6,3.09,8.9), BLUE),
             ((9.2,3.05,8.4),(10.6,3.09,8.9),(9.2,3.09,8.9), BLUE)]
    # 港湾潜艇（水面航行）
    for (sx2, sz2) in [(1.8, 14.2)]:
        sub = ellipse_mesh([(-1.5,0.20,0.18,0.06),(-0.7,0.28,0.24,0.08),(0.3,0.30,0.26,0.08),
                            (1.1,0.16,0.12,0.06),(1.6,0.05,0.04,0.05)], (0x24,0x3A,0x52))
        tris += [((p0[0]+sx2, p0[1], p0[2]+sz2), (p1[0]+sx2, p1[1], p1[2]+sz2),
                  (p2[0]+sx2, p2[1], p2[2]+sz2), c) for (p0, p1, p2, c) in sub]
        tris += bevel_box(sx2, 0.32, sz2+0.1, 0.30, 0.30, 0.72, 0.05, (0x24,0x3A,0x52))

    # ---- 中国阵营：合成营成建制（三三制），装备数量按真实编制缩景 ----
    def rot_box(x, z, yaw, cx, cy, cz, w, h, d, col, bev=0.04):
        ca, sa = math.cos(yaw), math.sin(yaw)
        out = []
        for (p0, p1, p2, c0) in bevel_box(cx, cy, cz, w, h, d, bev, col):
            rr = []
            for p in (p0, p1, p2):
                rr.append((x + p[0]*ca - p[2]*sa, p[1], z + p[0]*sa + p[2]*ca))
            out.append((rr[0], rr[1], rr[2], c0))
        return out

    def field_wear(x, z, yaw, hw, hh, hd, col):
        # 做旧三件：下缘泥污带 + 棱线磨损露底 + 锈迹流挂，近景单车三处可辨
        mud  = (0x4E,0x42,0x33)
        bare = tuple(min(255, max(0, int(col[i]*1.4))) for i in range(3))
        rust = (0x6B,0x4A,0x2E)
        for sx in (-1, 1):   # 两侧下沿泥污带
            tris.extend(rot_box(x, z, yaw, sx*hw, 0.13, 0, 0.045, 0.11, hd*1.7, mud, 0.02))
        tris.extend(rot_box(x, z, yaw, 0, 0.11, -hd, hw*1.5, 0.13, 0.06, mud, 0.02))  # 车尾横泥带
        tris.extend(rot_box(x, z, yaw, hw*0.6, hh+0.005, hd*0.45, 0.14, 0.025, 0.24, bare, 0.005))  # 上棱磨损露底
        tris.extend(rot_box(x, z, yaw, -hw*0.5, hh+0.005, -hd*0.35, 0.12, 0.025, 0.20, bare, 0.005))
        rust = tuple(min(255, int(c*1.15)) for c in rust)
        for (lx, lz) in ((hw*0.92, -hd*0.45), (-hw*0.86, hd*0.28)):  # 侧下锈迹流挂两道
            tris.extend(rot_box(x, z, yaw, lx, hh*0.5, lz, 0.038, hh*0.85, 0.07, rust, 0.004))

    def mbt(x, z, yaw):
        # 99A：履带 + 车体 + 楔形炮塔 + 附加装甲 + 遥感武器站 + 滑膛炮
        # 逐车漆面色差：同一迷彩下各车明暗不同
        jv = dr.uniform(-0.06, 0.06)
        VC = tuple(min(255, max(0, int(BLUE[i]*(1.0+jv)))) for i in range(3))
        tm = track_mesh(yaw)
        tris.extend([((p0[0]+x, p0[1], p0[2]+z), (p1[0]+x, p1[1], p1[2]+z),
                      (p2[0]+x, p2[1], p2[2]+z), c) for (p0, p1, p2, c) in tm])
        tris.extend(rot_box(x, z, yaw, 0, 0.34, 0, 1.15, 0.36, 2.3, VC, 0.06))
        tris.extend(rot_box(x, z, yaw, 0, 0.66, -0.1, 0.78, 0.26, 1.0, VC, 0.05))
        tris.extend(rot_box(x, z, yaw, 0, 0.78, -0.42, 0.92, 0.14, 0.5, VC, 0.06))
        tris.extend(rot_box(x, z, yaw, 0.26, 0.9, 0.25, 0.14, 0.12, 0.5, (0x2A,0x3E,0x60)))
        tris.extend(rot_box(x, z, yaw, 0, 0.62, 0.95, 0.075, 0.075, 1.35, DARK, 0.01))
        tris.extend(rot_box(x, z, yaw, -0.34, 0.44, -0.9, 0.2, 0.14, 0.2, VC, 0.02))
        # 随车备件：炮塔后部备用履带板 + 车尾油桶两只 + 车长机枪
        for (lx, lz) in ((-0.15, -0.86), (0.10, -0.88)):
            tris.extend(rot_box(x, z, yaw, lx, 0.86, lz, 0.16, 0.04, 0.22, (0x35,0x3B,0x40), 0.005))
        for lx in (-0.30, -0.12):
            tris.extend(rot_box(x, z, yaw, lx, 0.52, -1.18, 0.13, 0.22, 0.09, (0x3E,0x44,0x3A), 0.01))
        tris.extend(rot_box(x, z, yaw, 0.30, 0.96, -0.30, 0.03, 0.10, 0.42, DARK, 0.005))
        # 烟雾弹发射器：炮塔两侧各一簇三管
        for sx in (-0.42, 0.42):
            for k in range(3):
                ca2, sa2 = math.cos(yaw), math.sin(yaw)
                lx, lz = sx, -0.28 + k*0.075
                wx_, wz_ = x + lx*ca2 - lz*sa2, z + lx*sa2 + lz*ca2
                tris.extend(cone(wx_, 0.74, wz_, 0.022, 0.09, (0x2A,0x2C,0x2E), segs=4))
        # 天线：炮塔右后两根细杆
        for (lx, lz) in ((0.34, -0.55), (0.42, -0.50)):
            ca2, sa2 = math.cos(yaw), math.sin(yaw)
            wx_, wz_ = x + lx*ca2 - lz*sa2, z + lx*sa2 + lz*ca2
            tris.extend(cone(wx_, 1.0, wz_, 0.012, 0.75, DARK, segs=4))
        # 排气筒：车体右后
        tris.extend(rot_box(x, z, yaw, 0.62, 0.42, -0.95, 0.10, 0.20, 0.16, (0x2A,0x2C,0x2E), 0.02))
        # 侧裙板：压住履带与车体的衔接硬边，带波浪下缘
        for sx in (-0.66, 0.66):
            tris.extend(rot_box(x, z, yaw, sx, 0.30, 0, 0.06, 0.22, 2.1, BLUE, 0.03))
            for k in range(5):
                tris.extend(rot_box(x, z, yaw, sx, 0.20, -0.9 + k*0.45, 0.05, 0.10, 0.30, (0x3A,0x54,0x7E), 0.02))
        field_wear(x, z, yaw, 0.66, 0.52, 1.15, VC)

    def ifv(x, z, yaw):
        # 轮式步战车：8轮底盘 + 炮塔 + 机关炮 + 外挂背囊
        jv = dr.uniform(-0.06, 0.06)
        VC = tuple(min(255, max(0, int(BLUE[i]*(1.0+jv)))) for i in range(3))
        tris.extend(rot_box(x, z, yaw, 0, 0.30, 0, 1.05, 0.32, 2.1, VC, 0.06))
        tris.extend(rot_box(x, z, yaw, 0, 0.56, 0.3, 0.62, 0.24, 0.8, VC, 0.05))
        tris.extend(rot_box(x, z, yaw, 0, 0.56, 0.95, 0.06, 0.06, 0.8, DARK, 0.01))
        tris.extend(rot_box(x, z, yaw, -0.42, 0.5, -0.6, 0.16, 0.14, 0.3, (0x3E,0x44,0x3A)))
        tris.extend(rot_box(x, z, yaw, 0.40, 0.54, -0.55, 0.14, 0.20, 0.26, (0x3E,0x44,0x3A), 0.01))
        # 天线：车顶两根细杆
        for (lx, lz) in ((0.4, -0.9), (0.48, -0.75)):
            ca2, sa2 = math.cos(yaw), math.sin(yaw)
            wx_, wz_ = x + lx*ca2 - lz*sa2, z + lx*sa2 + lz*ca2
            tris.extend(cone(wx_, 0.85, wz_, 0.012, 0.7, DARK, segs=4))
        ca, sa = math.cos(yaw), math.sin(yaw)
        for ax in (-0.7, -0.25, 0.2, 0.65):
            for sx in (-0.5, 0.5):
                wx_, wz_ = x + sx*ca - ax*sa, z + sx*sa + ax*ca
                tris.extend(cone(wx_, 0.14, wz_, 0.13, 0.14, DARK, segs=6))
        field_wear(x, z, yaw, 0.53, 0.46, 1.05, VC)

    def spg(x, z, yaw):
        # 自行加榴炮：履带 + 高仰角长炮管 + 炮口制退器（炮群对向红方阵地）
        jv = dr.uniform(-0.06, 0.06)
        VC = tuple(min(255, max(0, int(BLUE[i]*(1.0+jv)))) for i in range(3))
        tm = track_mesh(yaw)
        tris.extend([((p0[0]+x, p0[1], p0[2]+z), (p1[0]+x, p1[1], p1[2]+z),
                      (p2[0]+x, p2[1], p2[2]+z), c) for (p0, p1, p2, c) in tm])
        tris.extend(rot_box(x, z, yaw, 0, 0.34, 0, 1.2, 0.40, 2.0, VC, 0.06))
        tris.extend(rot_box(x, z, yaw, 0, 0.68, -0.1, 0.95, 0.30, 0.9, VC, 0.05))
        ca2, sa2 = math.cos(yaw), math.sin(yaw)
        bx_, bz_ = x - 0.3*sa2, z + 0.3*ca2
        tris.extend(cone(bx_, 0.86, bz_, 0.035, 1.05, DARK, segs=6, tilt=0.42))
        bx2_, bz2_ = x - 0.62*sa2, z + 0.62*ca2
        tris.extend(cone(bx2_, 1.24, bz2_, 0.05, 0.13, DARK, segs=6))
        field_wear(x, z, yaw, 0.60, 0.54, 1.00, VC)

    def aa(x, z, yaw):
        # 野战防空车：履带 + 相控阵平板 + 四联装发射箱
        jv = dr.uniform(-0.06, 0.06)
        VC = tuple(min(255, max(0, int(BLUE[i]*(1.0+jv)))) for i in range(3))
        tm = track_mesh(yaw)
        tris.extend([((p0[0]+x, p0[1], p0[2]+z), (p1[0]+x, p1[1], p1[2]+z),
                      (p2[0]+x, p2[1], p2[2]+z), c) for (p0, p1, p2, c) in tm])
        tris.extend(rot_box(x, z, yaw, 0, 0.34, 0, 1.2, 0.38, 2.0, VC, 0.06))
        tris.extend(rot_box(x, z, yaw, 0, 0.62, 0.2, 0.8, 0.22, 1.0, VC, 0.04))
        tris.extend(rot_box(x, z, yaw, 0, 0.78, 0.2, 1.0, 0.10, 0.7, (0x3A,0x54,0x7E)))
        tris.extend(rot_box(x, z, yaw, -0.3, 0.86, -0.1, 0.55, 0.20, 0.5, (0x2A,0x3E,0x60)))
        field_wear(x, z, yaw, 0.60, 0.53, 1.00, VC)

    def truck(x, z, yaw):
        # 保障卡车：驾驶楼 + 帆布货厢
        tris.extend(rot_box(x, z, yaw, 0, 0.24, 0, 0.95, 0.28, 1.0, BLUE, 0.05))
        tris.extend(rot_box(x, z, yaw, 0, 0.50, 0.62, 0.85, 0.26, 0.5, BLUE, 0.05))
        tris.extend(rot_box(x, z, yaw, 0, 0.52, -0.45, 0.95, 0.36, 1.3, (0x3E,0x44,0x3A), 0.03))
        field_wear(x, z, yaw, 0.48, 0.38, 0.50, BLUE)
        ca, sa = math.cos(yaw), math.sin(yaw)
        for ax in (-0.7, 0.3):
            for sx in (-0.48, 0.48):
                wx_, wz_ = x + sx*ca - ax*sa, z + sx*sa + ax*ca
                tris.extend(cone(wx_, 0.15, wz_, 0.14, 0.15, DARK, segs=6))

    def mlrs(x, z, yaw):
        # 远程火箭炮：车头 + 两组五联装模块化发射箱
        tris.extend(rot_box(x, z, yaw, 0, 0.24, 0.85, 0.9, 0.28, 0.6, BLUE, 0.05))
        tris.extend(rot_box(x, z, yaw, 0, 0.26, -0.2, 0.95, 0.32, 1.8, BLUE, 0.05))
        tris.extend(rot_box(x, z, yaw, -0.26, 0.52, -0.15, 0.45, 0.32, 1.5, (0x3E,0x44,0x3A), 0.03))
        tris.extend(rot_box(x, z, yaw, 0.26, 0.52, -0.15, 0.45, 0.32, 1.5, (0x3E,0x44,0x3A), 0.03))
        # 发射箱细节：前端面五联装管口分隔条 + 箱顶加强筋 + 液压升降柱 + 车后备弹舱
        for sx in (-0.26, 0.26):
            for k in range(5):
                off = -0.17 + k*0.085
                tris.extend(rot_box(x, z, yaw, sx+off, 0.685, 0.58, 0.055, 0.055, 0.03, DARK, 0.008))   # 管口
                tris.extend(rot_box(x, z, yaw, sx+off, 0.695, -0.15, 0.05, 0.02, 1.4, (0x2E,0x33,0x2C), 0.005))  # 箱顶筋
            tris.extend(rot_box(x, z, yaw, sx, 0.40, -0.05, 0.10, 0.16, 0.10, (0x4A,0x50,0x46), 0.01))  # 液压柱
        tris.extend(rot_box(x, z, yaw, 0, 0.30, 1.05, 0.7, 0.18, 0.35, (0x3E,0x44,0x3A), 0.02))  # 备弹舱
        field_wear(x, z, yaw, 0.48, 0.42, 0.90, BLUE)
        ca, sa = math.cos(yaw), math.sin(yaw)
        for ax in (-0.65, -0.1, 0.45):
            for sx in (-0.48, 0.48):
                wx_, wz_ = x + sx*ca - ax*sa, z + sx*sa + ax*ca
                tris.extend(cone(wx_, 0.15, wz_, 0.13, 0.14, DARK, segs=6))

    def j20(x, y, z, yaw):
        # 歼击机：菱形机身 + 鸭翼 + 后掠主翼 + 双垂尾（三机编队）
        ca, sa = math.cos(yaw), math.sin(yaw)
        def rot_tri(t):
            rr = []
            for p in t[:3]:
                rr.append((x + p[0]*ca - p[2]*sa, p[1], z + p[0]*sa + p[2]*ca))
            return (rr[0], rr[1], rr[2], t[3])
        tris.extend([rot_tri(t) for t in
            [((0, y, -0.9), (0.16, y+0.12, 0.4), (0.16, y, 0.4), BLUE),
             ((0, y, -0.9), (-0.16, y+0.12, 0.4), (-0.16, y, 0.4), BLUE),
             ((0.16, y, 0.4), (0.16, y, 0.7), (0, y, -0.9), BLUE),
             ((-0.16, y, 0.4), (-0.16, y, 0.7), (0, y, -0.9), BLUE),
             ((0, y+0.14, 0.1), (0, y+0.10, 0.9), (0, y, 0.9), (0x3A,0x54,0x7E))]])
        tris.extend([rot_tri(t) for t in
            [((0.16, y, 0.15), (1.15, y, 0.75), (1.15, y, 0.95), BLUE),
             ((0.16, y, 0.15), (1.15, y, 0.95), (0.16, y, 0.45), BLUE),
             ((-0.16, y, 0.15), (-1.15, y, 0.75), (-1.15, y, 0.95), BLUE),
             ((-0.16, y, 0.15), (-1.15, y, 0.95), (-0.16, y, 0.45), BLUE),
             ((0.1, y, 0.9), (0.55, y, 1.05), (0.55, y, 1.2), BLUE),
             ((-0.1, y, 0.9), (-0.55, y, 1.05), (-0.55, y, 1.2), BLUE),
             ((0.1, y+0.1, 0.75), (0.3, y+0.55, 0.95), (0.3, y+0.1, 0.95), BLUE),
             ((-0.1, y+0.1, 0.75), (-0.3, y+0.55, 0.95), (-0.3, y+0.1, 0.95), BLUE)]])

    def z20(x, y, z):
        # 直升机：流线机身 + 低置尾梁 + 主旋翼 + 垂尾
        tris.extend([((p0[0]+x, p0[1]+y, p0[2]+z), (p1[0]+x, p1[1]+y, p1[2]+z),
                      (p2[0]+x, p2[1]+y, p2[2]+z), c)
                     for (p0, p1, p2, c) in ellipse_mesh([(0.0,0.16,0.14,1.5),(0.6,0.12,0.10,1.4),
                                                         (1.5,0.05,0.04,1.0),(1.9,0.03,0.03,0.9)], BLUE)])
        for ang in range(5):
            a = ang * 2 * math.pi / 5
            tris.append(((x, y+0.30, z), (x+0.95*math.cos(a), y+0.30, z+0.95*math.sin(a)),
                         (x+0.95*math.cos(a+0.35), y+0.30, z+0.95*math.sin(a+0.35)), DARK))
        tris.extend([((x+1.6, y+0.22, z-0.35), (x+1.6, y+0.22, z+0.35), (x+1.95, y+0.22, z+0.35), BLUE),
                     ((x+1.6, y+0.22, z-0.35), (x+1.95, y+0.22, z+0.35), (x+1.95, y+0.22, z-0.35), BLUE)])
        tris.append(((x+1.9, y+0.22, z), (x+1.9, y+0.62, z), (x+1.98, y+0.22, z), BLUE))  # 垂尾

    def ddg(x, z, yaw):
        # 驱逐舰：长舰体 + 桥楼 + 相控阵平板 + 垂发井 + 主炮 + 机库
        ca, sa = math.cos(yaw), math.sin(yaw)
        def rp(px, py, pz):
            return (x + px*ca - pz*sa, py, z + px*sa + pz*ca)
        hull_c = (0x24,0x3A,0x52)
        tris.extend(rot_box(x, z, yaw, 0, 0.10, 0, 1.3, 0.20, 4.2, hull_c, 0.08))
        tris.extend(rot_box(x, z, yaw, 0, 0.30, 0.9, 0.95, 0.24, 1.5, hull_c, 0.06))   # 前桥楼
        tris.extend(rot_box(x, z, yaw, 0, 0.30, -1.1, 0.85, 0.24, 1.3, hull_c, 0.06))  # 机库
        tris.extend(rot_box(x, z, yaw, 0, 0.62, 0.9, 0.5, 0.35, 0.6, (0x3A,0x54,0x7E), 0.04))
        tris.extend(rot_box(x, z, yaw, 0, 0.55, 0.25, 0.7, 0.08, 0.18, (0x3A,0x54,0x7E), 0.01))  # 相控阵
        tris.extend(rot_box(x, z, yaw, 0, 0.55, -0.25, 0.7, 0.08, 0.18, (0x3A,0x54,0x7E), 0.01))
        for r0 in range(2):
            for c0 in range(4):
                tris.extend(rot_box(x, z, yaw, -0.15+c0*0.10, 0.26, 1.85-r0*0.22, 0.08, 0.14, 0.18, DARK, 0.01))  # 垂发
        tris.extend(rot_box(x, z, yaw, 0, 0.32, 2.0, 0.14, 0.14, 0.45, DARK, 0.01))    # 主炮
        tris.extend(rot_box(x, z, yaw, 0, 0.55, 1.75, 0.06, 0.30, 0.06, DARK, 0.01))   # 桅杆
        tris.extend(rot_box(x, z, yaw, 0, 0.93, 1.75, 0.015, 0.16, 0.11, (0xB8,0x3A,0x2E), 0.005))  # 桅顶信号旗
        # 直升机起降坪：尾部甲板深色圆面 + 圆环标线
        tris.extend(rot_box(x, z, yaw, 0, 0.21, -2.1, 1.05, 0.015, 1.3, (0x1E,0x2C,0x3E), 0.005))
        tris.extend(rot_box(x, z, yaw, 0, 0.215, -2.1, 0.72, 0.015, 0.72, (0x2E,0x5E,0x8C), 0.005))
        # 系缆桩：甲板四角小柱
        for (lx, lz) in ((-0.5, 1.9), (0.5, 1.9), (-0.5, -2.6), (0.5, -2.6)):
            tris.extend(rot_box(x, z, yaw, lx, 0.24, lz, 0.045, 0.08, 0.045, DARK, 0.01))
        # 两舷栏杆：前后段细横杆
        for lz0 in (0.0, -1.0, -1.6):
            for sx0 in (-0.64, 0.64):
                tris.extend(rot_box(x, z, yaw, sx0, 0.30, lz0, 0.015, 0.012, 0.55, DARK, 0.005))
        # 舰艏折角：主炮前小V形甲板
        tris.extend(rot_box(x, z, yaw, 0, 0.16, 2.35, 0.7, 0.06, 0.4, hull_c, 0.03))

    def gmv(x, z, yaw, col):
        # 轻型高机动车：尖头引擎盖 + 低驾驶舱 + 防滚架 + 帆布货斗 + 备胎，车斗载2名乘员
        jv = dr.uniform(-0.06, 0.06)
        col = tuple(min(255, max(0, int(col[i]*(1.0+jv)))) for i in range(3))
        tris.extend(rot_box(x, z, yaw, 0, 0.36, 0, 1.05, 0.40, 2.6, col, 0.06))
        tris.extend(rot_box(x, z, yaw, 0, 0.60, 0.82, 0.88, 0.18, 0.72, col, 0.05))   # 引擎盖
        tris.extend(rot_box(x, z, yaw, 0, 0.72, 0.44, 0.84, 0.20, 0.04, (0x2A,0x38,0x44), 0.01))  # 挡风玻璃
        tris.extend(rot_box(x, z, yaw, 0, 0.56, 0.26, 0.94, 0.28, 0.40, col, 0.05))   # 驾驶舱
        for lx in (-0.42, 0.42):                                                       # 防滚架
            tris.extend(rot_box(x, z, yaw, lx, 0.88, -0.32, 0.05, 0.48, 0.05, DARK, 0.01))
        tris.extend(rot_box(x, z, yaw, 0, 1.12, -0.32, 0.90, 0.04, 0.04, DARK, 0.01))
        tris.extend(rot_box(x, z, yaw, 0, 0.55, -0.78, 0.94, 0.30, 0.95, (0x3E,0x44,0x3A), 0.04))  # 货斗
        tris.extend(cone(x + 0.0*math.cos(yaw), 0.34, z - 1.32, 0.24, 0.10, DARK, segs=6))         # 尾部备胎
        tris.extend(rot_box(x, z, yaw, 0.40, 0.92, -0.95, 0.02, 0.50, 0.02, DARK, 0.005))          # 天线
        ca, sa = math.cos(yaw), math.sin(yaw)
        for ax in (-0.85, 0.85):                                                       # 车轮
            for sx in (-0.52, 0.52):
                wx_, wz_ = x + sx*ca - ax*sa, z + sx*sa + ax*ca
                tris.extend(cone(wx_, 0.16, wz_, 0.17, 0.13, DARK, segs=6))
        # 车斗乘员两名：露肩戴盔，随车机动
        for lx in (-0.22, 0.22):
            wx_, wz_ = x + lx*ca - (-0.55)*sa, z + lx*sa + (-0.55)*ca
            tris.extend(bevel_box(wx_, 0.74, wz_, 0.16, 0.22, 0.12, 0.02, (0x33,0x3A,0x30)))
            tris.extend(cone(wx_, 0.90, wz_, 0.075, 0.09, (0x33,0x3A,0x30), segs=6))

    # 合成营部署：3个装步连（9车/连）+ 坦克连（10车）+ 炮兵连（6门）+ 防空排（3）+ 保障排（3）+ 营部
    for (co_x, co_z) in [(21.5, 2.0), (26.2, 2.0), (21.5, 8.8)]:
        for r in range(3):
            for (dx, dz) in [(0, 0), (-1.4, 1.6), (1.4, 1.6)]:
                ifv(co_x + dx, co_z + r*3.4 + dz, 0.05*r)
    for r in range(3):
        for (dx, dz) in [(0, 0), (-1.5, 1.7), (1.5, 1.7)]:
            mbt(31.5 + dx, 2.0 + r*3.4 + dz, 0.02)
    mbt(36.2, 3.7, 0.0)   # 坦克连长车
    for i in range(6):
        spg(22.5 + (i % 3)*2.6, 13.2 + (i // 3)*2.3, math.pi)
    for i in range(3):
        aa(19.6 + i*2.4, 15.2, 0.0)
    for i in range(3):
        truck(37.2, 12.2 + i*1.9, math.pi/2)
    mlrs(33.8, 15.4, 0.1); mlrs(36.4, 15.4, 0.1)
    ifv(30.2, 13.4, 0.0)  # 营部指挥车
    fireteam(31.4, 14.4, BLUE, 0.1); fireteam(29.2, 14.6, BLUE, -0.2)
    # 合成营随车步兵：每连一组战斗小组在攻击队形侧翼
    fireteam(22.8, 6.9, BLUE, 0.3); fireteam(27.4, 6.9, BLUE, -0.3); fireteam(23.0, 13.7, BLUE, 0.0)
    # 堑壕与沙袋工事：营区前沿一排 + 两翼沙袋墙 + 阵地内交通壕（驻防观感）
    SAND = (0x9A,0x8F,0x76); SAND2 = (0x8A,0x7F,0x66); TRENCH = (0x46,0x3A,0x2E)
    def sandbag_row(x0, z0, yaw, n):
        c2, s2 = math.cos(yaw), math.sin(yaw)
        for i in range(n):
            for lv in range(2):
                ox, oz = (i*0.34 - n*0.17, lv*0.36)
                wx_, wz_ = x0 + ox*c2 + oz*s2, z0 - ox*s2 + oz*c2
                col = SAND if (i+lv) % 2 == 0 else SAND2
                tris.extend(rot_box(wx_, wz_, yaw, 0, 0.09+lv*0.16, 0, 0.30, 0.15, 0.19, col, 0.03))
    def trench_line(x0, z0, x1, z1):
        seg = 14
        for i in range(seg):
            t0 = i/seg; t1 = (i+0.96)/seg
            mx, mz = x0+(x1-x0)*t0, z0+(z1-z0)*t0
            L = math.hypot(x1-x0, z1-z0)
            tris.extend(rot_box(mx, mz, math.atan2(-(z1-z0), x1-x0),
                        0, 0.02, 0, L/seg, 0.012, 0.9, TRENCH, 0.0))
    # 前沿主堑壕：横在营区与红方之间
    trench_line(41.5, 1.5, 41.5, 13.5)
    # 堑壕里两个战斗小组压阵
    fireteam(41.5, 4.2, BLUE, -math.pi/2); fireteam(41.5, 9.6, BLUE, -math.pi/2)
    # 前沿沙袋墙：堑壕前缘错位两段
    sandbag_row(42.6, 3.8, math.pi/2, 16)
    sandbag_row(42.6, 10.2, math.pi/2, 12)
    # 两翼沙袋：炮兵阵地侧后与营部侧
    sandbag_row(19.2, 13.6, 0.0, 12)
    sandbag_row(29.6, 17.4, 0.0, 18)
    # 交通壕：从营部通向前沿
    trench_line(38.6, 13.8, 41.3, 11.8)
    trench_line(38.4, 14.4, 41.2, 5.0)
    # 海军：港湾驻泊编队——三舰靠帮一列（主舰居中，两舷护舷垫贴靠）
    ddg(4.6, 14.4, math.pi/2)
    ddg(4.6, 13.0, math.pi/2)
    ddg(4.6, 11.55, math.pi/2)
    # 靠帮缝隙护舷垫：两道缝各三块黑垫
    for gz_ in (13.68, 13.72, 13.64):
        tris.extend(rot_box(4.6, gz_, 0.0, 0.0, 0.06, gz_, 0.5, 0.10, 0.18, (0x18,0x18,0x18), 0.01))
    for gz_ in (12.24, 12.28, 12.20):
        tris.extend(rot_box(4.6, gz_, 0.0, 0.0, 0.06, gz_, 0.5, 0.10, 0.18, (0x18,0x18,0x18), 0.01))
    # 锚泊浮标：舰列外侧两只橙红浮筒（水线小圆锥+暗色底环）
    for (bx_, bz_) in [(2.9, 10.2), (3.1, 16.6)]:
        tris += cone(bx_, 0.02, bz_, 0.22, 0.42, (0xC8,0x5A,0x28), segs=6)
        tris += cone(bx_, 0.0, bz_, 0.30, 0.10, (0x2A,0x2A,0x2A), segs=6)
    # 码头哨兵：主舰正对岸缘立岗
    soldier(7.0, 14.4, BLUE, 'stand', -math.pi/2)
    # 轻型高机动车队：乘车机动、下车战斗（营属侦察/突击分队沿营区南侧道路纵队）
    gmv(24.0, 18.6, 0.0, BLUE); gmv(28.0, 18.6, 0.0, BLUE); gmv(32.0, 18.6, 0.0, BLUE)
    fireteam(24.9, 17.4, BLUE, 0.0); fireteam(28.9, 17.4, BLUE, 0.0); fireteam(32.9, 17.4, BLUE, 0.0)
    # 红方对应建制：前沿纵队 + 下车班组伴随
    gmv(55.0, 17.6, math.pi, RED); gmv(55.0, 20.6, math.pi, RED); gmv(55.0, 23.6, math.pi, RED)
    fireteam(54.2, 18.8, RED, math.pi); fireteam(54.2, 21.8, RED, math.pi); fireteam(54.2, 24.8, RED, math.pi)

    # 空军：三机编队掠过营上空 + 直升机低空进入
    j20(23.0, 5.0, 7.0, 0.0); j20(26.6, 5.3, 5.2, -0.05); j20(26.6, 5.3, 8.8, 0.05)
    z20(19.5, 0.0, 11.2)

    # ---- 战斗剧本 · 阶段一「海空准备」首班要素 ----
    # 海峡线：驱逐舰单纵队进占射击阵位，舰尾拖白色尾迹（港湾靠泊舰不动）
    WAKE1 = (0xE2, 0xE2, 0xD8); WAKE2 = (0xC4, 0xCE, 0xD2)
    for (sx_, sz_, sy_) in [(48.3, 9.0, math.pi), (48.6, 15.2, math.pi*0.98), (48.9, 21.4, math.pi*1.02)]:
        ddg(sx_, sz_, sy_)
        rot_box(sx_, sz_, 0.0, 0.0, 0.035, 3.4, 0.55, 0.02, 1.8, WAKE1, 0.008)   # 舰尾白沫段
        rot_box(sx_, sz_, 0.0, 0.0, 0.030, 5.2, 0.36, 0.02, 2.4, WAKE2, 0.008)   # 尾迹渐散段
    # 红方纵深：舰炮急袭弹着——水柱+烟柱成列（火力打纵深不打水际，滩头正面不放）
    sr = random.Random(20261106)
    for (bx_, bz_) in [(59.5, 10.5), (62.0, 15.0), (60.8, 19.5), (64.0, 23.0), (65.5, 27.0)]:
        sc = sr.uniform(0.85, 1.15)
        tris += rot_box(bx_, bz_, sr.uniform(0, math.pi), 0, 0.02, 0, 1.3, 0.015, 1.3,
                        (0x50, 0x48, 0x3E), 0.0)                                  # 焦土圈
        tris += cone(bx_, 0.02, bz_, 0.45*sc, 1.2*sc, (0xD6, 0xD0, 0xBE), segs=5,
                     tilt=-0.75)                                                   # 水沫西斜喷
        tris += cone(bx_, 0.02, bz_, 0.40*sc, 1.0*sc, (0xC8, 0xC2, 0xB0), segs=5,
                     tilt=0.85)                                                    # 水沫东斜喷
        tris += cone(bx_, 0.15, bz_, 1.00*sc, 2.2*sc, (0x74, 0x6A, 0x5E), segs=6,
                     tilt=0.55*sc)                                                 # 主烟顺风倒伏
        tris += cone(bx_ + 0.9*sc, 0.05, bz_ + sr.uniform(-0.5, 0.5), 1.15*sc,
                     1.1*sc, (0x8E, 0x84, 0x78), segs=6, tilt=0.8)                 # 贴地副烟团
    # 海峡上空：歼击机双机沿走廊进入（机身+翼尖凝结尾迹）
    j20(47.5, 4.2, 19.5, math.pi - 0.04)
    j20(49.6, 4.5, 17.8, math.pi + 0.05)
    for (cx_, cz_, cy_) in [(46.35, 17.1, 4.24), (48.65, 17.1, 4.24),
                            (48.45, 15.3, 4.54), (50.75, 15.3, 4.54)]:
        rot_box(cx_, cz_, 0.0, 0.0, cy_, 0.0, 0.06, 0.03, 2.4, (0xD8, 0xDC, 0xDE), 0.005)

    # ---- 战斗剧本 · 阶段一第二班「直升机掠海侦察波次」 ----
    # 海面侦察直升机：缩比机身 + 六叶浅灰细旋翼（避免大黑 X 读成风车）
    def helo_sea(x, y, z):
        sc = 0.85
        tris.extend([((p0[0]*sc+x, p0[1]*sc+y, p0[2]*sc+z),
                      (p1[0]*sc+x, p1[1]*sc+y, p1[2]*sc+z),
                      (p2[0]*sc+x, p2[1]*sc+y, p2[2]*sc+z), c)
                     for (p0, p1, p2, c) in ellipse_mesh([(0.0, 0.16, 0.14, 1.5),
                                                          (0.6, 0.12, 0.10, 1.4),
                                                          (1.5, 0.05, 0.04, 1.0),
                                                          (1.9, 0.03, 0.03, 0.9)], BLUE)])
        for ang in range(6):
            a = ang * 2 * math.pi / 6
            tris.append(((x, y+0.28, z), (x+0.82*math.cos(a), y+0.28, z+0.82*math.sin(a)),
                         (x+0.82*math.cos(a+0.30), y+0.28, z+0.82*math.sin(a+0.30)),
                         (0x6E, 0x76, 0x7E)))
        tris.extend([((x+1.36, y+0.19, z-0.30), (x+1.36, y+0.19, z+0.30), (x+1.63, y+0.19, z+0.30), BLUE),
                     ((x+1.36, y+0.19, z-0.30), (x+1.63, y+0.19, z+0.30), (x+1.63, y+0.19, z-0.30), BLUE)])
        tris.append(((x+1.62, y+0.19, z), (x+1.62, y+0.55, z), (x+1.70, y+0.19, z), BLUE))
        # 桨盘模糊：旋翼下浅灰圆盘，把「X」读成旋转旋翼面
        for k in range(12):
            a = k * 2 * math.pi / 12
            rot_box(x + 0.5*math.cos(a), z + 0.5*math.sin(a), a + math.pi/2,
                    0, y+0.265, 0, 0.24, 0.006, 0.10, (0x9A, 0xA2, 0xA8), 0.003)
    # 三机楔形波次低空掠海进入（高度 2.5~2.9m，舰桥之上，朝红方岸侦察），水面带机影+下洗环形波纹
    for (hx_, hz_, hy_, hr_) in [(47.0, 26.0, 2.80, 0.0),
                                 (46.4, 24.8, 2.55, 0.06),
                                 (47.2, 27.6, 2.65, -0.05)]:
        helo_sea(hx_, hy_, hz_)
        # 水面机影：深色扁块贴浪面，让机身读得出「悬在水面之上」
        rot_box(hx_, hz_, 0.0, 0, 0.02, 0, 1.20, 0.012, 0.45, (0x1E, 0x40, 0x5C), 0.006)
        # 下洗波纹：每机两圈同心环，外圈偏白带碎沫感，内圈更实（抬到浪面之上）
        for (rr_, col_) in [(1.45, (0xC8, 0xCE, 0xD0)), (0.90, (0xD8, 0xDE, 0xDE))]:
            seg_n = 10
            for k in range(seg_n):
                a0 = k * 2 * math.pi / seg_n + hr_
                seg_cx, seg_cz = hx_ + rr_ * math.cos(a0), hz_ + rr_ * math.sin(a0)
                rot_box(seg_cx, seg_cz, a0 + math.pi / 2, 0, 0.025, 0,
                        seg_n and 2 * math.pi * rr_ / seg_n * 0.62, 0.008, 0.13, col_, 0.004)

    # ---- 红方阵地加料：前沿堑壕+沙袋墙+炮兵/防空/火箭炮/保障车队+步兵 ----
    # 前沿两段堑壕 + 守备步兵
    trench_line(54.8, 1.2, 54.8, 3.6)
    trench_line(54.8, 8.6, 54.8, 11.8)
    fireteam(54.8, 2.4, RED, math.pi/2); fireteam(54.8, 10.6, RED, math.pi/2)
    # 沙袋墙护住堑壕后缘
    sandbag_row(53.9, 2.2, math.pi/2, 10)
    sandbag_row(53.9, 10.4, math.pi/2, 10)
    # 自行火炮两门：对向蓝方海岛
    for (ax_, az_) in [(56.8, 4.0), (56.8, 8.2)]:
        tm = track_mesh(math.pi)
        tris += [((p0[0]+ax_, p0[1], p0[2]+az_), (p1[0]+ax_, p1[1], p1[2]+az_),
                  (p2[0]+ax_, p2[1], p2[2]+az_), c) for (p0, p1, p2, c) in tm]
        tris += rot_box(ax_, az_, math.pi, 0, 0.36, 0, 1.15, 0.38, 2.0, RED, 0.06)
        tris += rot_box(ax_, az_, math.pi, 0, 0.70, -0.1, 0.9, 0.28, 0.85, RED, 0.05)
        tris += cone(ax_, 0.90, az_-0.35, 0.04, 1.15, DARK, segs=6, tilt=-0.42)
    # 防空车：雷达平板 + 发射箱
    tris += rot_box(57.6, 6.2, math.pi, 0, 0.34, 0, 1.1, 0.36, 1.9, RED, 0.05)
    tris += rot_box(57.6, 6.2, math.pi, 0, 0.60, 0.2, 0.75, 0.20, 0.9, RED, 0.04)
    tris += rot_box(57.6, 6.2, math.pi, 0, 0.76, 0.2, 0.95, 0.09, 0.65, (0x7E,0x3A,0x3A))
    tris += rot_box(57.6, 6.2, math.pi, -0.28, 0.84, -0.1, 0.5, 0.18, 0.45, (0x60,0x2A,0x2E))
    # 保障卡车两辆
    for i in range(2):
        tris += rot_box(56.2, 12.4 + i*2.0, math.pi/2, 0, 0.26, 0, 0.9, 0.30, 1.0, RED, 0.05)
        tris += rot_box(56.2, 12.4 + i*2.0, math.pi/2, 0, 0.52, 0.6, 0.8, 0.26, 0.5, RED, 0.05)
        tris += rot_box(56.2, 12.4 + i*2.0, math.pi/2, 0, 0.54, -0.5, 0.9, 0.36, 1.3, (0x4A,0x3E,0x36), 0.03)
    # 远程火箭炮一辆
    tris += rot_box(55.6, 14.2, math.pi*0.95, 0, 0.26, -0.2, 0.95, 0.32, 1.8, RED, 0.05)
    tris += rot_box(55.6, 14.2, math.pi*0.95, -0.26, 0.54, -0.15, 0.45, 0.32, 1.5, (0x4A,0x3E,0x36), 0.03)
    tris += rot_box(55.6, 14.2, math.pi*0.95, 0.26, 0.54, -0.15, 0.45, 0.32, 1.5, (0x4A,0x3E,0x36), 0.03)
    # 阵地腹地雷达站
    tris += bevel_box(58.0, 0.4, 15.5, 1.2, 0.8, 1.2, 0.08, (0x6E,0x44,0x44))
    tris += cone(58.0, 1.5, 15.5, 0.02, 1.0, DARK, segs=4)

    # 红方伪装网：火炮、雷达与火箭炮上方搭设斑点遮障网，四角立杆
    def camo_net(cx, cz, yaw, w, d, y0):
        c2, s2 = math.cos(yaw), math.sin(yaw)
        CAMO = [(0x4E,0x5A,0x3A), (0x5C,0x55,0x3A), (0x3E,0x4A,0x30), (0x66,0x5E,0x40)]
        cn = random.Random(int(cx*100)+int(cz*7))
        cols, rows = max(2, int(w/0.55)), max(2, int(d/0.55))
        for i in range(cols):
            for j in range(rows):
                lx = -w/2 + (i+0.5)*w/cols; lz = -d/2 + (j+0.5)*d/rows
                wx_, wz_ = cx + lx*c2 + lz*s2, cz - lx*s2 + lz*c2
                nx_, nz_ = (i+0.5)/cols - 0.5, (j+0.5)/rows - 0.5
                sag = 0.05*math.sin(i*1.7) + 0.04*math.cos(j*2.1) \
                      + 0.07*(nx_*nx_ + nz_*nz_)   # 边缘下垂更深，近看有波谷
                tris.extend(rot_box(wx_, wz_, yaw, 0, y0+sag, 0,
                            w/cols, 0.02, d/rows, CAMO[cn.randrange(4)], 0.005))
        for (lx, lz) in ((-w/2+0.05, -d/2+0.05), (w/2-0.05, -d/2+0.05),
                         (-w/2+0.05, d/2-0.05), (w/2-0.05, d/2-0.05)):
            wx_, wz_ = cx + lx*c2 + lz*s2, cz - lx*s2 + lz*c2
            tris.extend(cone(wx_, 0, wz_, 0.03, y0, DARK, segs=4))
    camo_net(56.8, 4.0, math.pi, 2.2, 3.0, 1.55)      # 自行火炮一
    camo_net(56.8, 8.2, math.pi, 2.2, 3.0, 1.55)      # 自行火炮二
    camo_net(55.6, 14.2, math.pi*0.95, 2.4, 2.6, 1.35) # 火箭炮
    camo_net(58.0, 15.5, 0.0, 2.0, 2.0, 1.55)         # 雷达站
    # 蓝方伪装对等化：炮兵阵地、火箭炮与营部车辆同样搭遮障网（只遮火器，不铺满营区）
    for (bx, bz) in [(22.5, 13.2), (25.1, 13.2), (27.7, 13.2)]:
        camo_net(bx, bz, math.pi, 1.9, 2.2, 1.28)     # 前排自行火炮
    camo_net(33.8, 15.4, 0.1, 1.9, 2.1, 1.30)         # 火箭炮一
    camo_net(36.4, 15.4, 0.1, 1.9, 2.1, 1.30)         # 火箭炮二
    camo_net(30.2, 13.4, 0.0, 1.9, 2.1, 1.32)         # 营部指挥车

    # 树与岩石
    r = random.Random(19491001)
    placed = 0
    while placed < 22:
        x, z = r.uniform(0, 60), r.uniform(0, 40)
        if 15.5 < x < 23.5 and 3.5 < z < 11.5: continue
        if x < 10 or x > 44 or z < 5.5 or z > 34: continue   # 避开海面、沙滩带与海峡
        if 21 < x < 36 and 17 < z < 20.2: continue            # 避开车队行进走廊
        if 19 < x < 40 and 0.5 < z < 17: continue
        if r.random() < 0.55:
            s = r.uniform(0.25, 0.6)
            j = r.uniform(-0.10, 0.10)
            rock_c = tuple(max(0, min(255, int(c*(1.0+j)+r.uniform(-6, 6)))) for c in ROCK)
            tris += cone(x, 0.1, z, s, s*1.2, rock_c, segs=5)
        else:
            h = r.uniform(0.9, 1.8)
            j = r.uniform(-0.13, 0.13)
            yj = r.uniform(-0.06, 0.10)
            leaf_c = tuple(max(0, min(255, int(c*(1.0+j+yj)))) for c in LEAF)
            leaf_c2 = tuple(min(255, int(c*(1.0+j+yj+0.16))) for c in LEAF)
            tris += cone(x, 0, z, 0.18, h*0.5, TRUNK, segs=5)
            tris += cone(x, h*0.55, z, 0.45, h*0.85, leaf_c, segs=8)
            # 树冠双层：顶部再叠一顶稍浅的叶色，整树不再是一块纯色
            tris += cone(x, h*0.78, z, 0.28, h*0.42, leaf_c2, segs=7)
        placed += 1

    # 小岛点缀：每座小岛一两棵树 + 一块岩石，避免光秃
    ir = random.Random(314159)
    for (cx, cz, rx2, ry2) in ISLETS:
        for k in range(3):
            a = ir.uniform(0, 6.28); rr = ir.uniform(0.15, 0.55)
            ix_, iz_ = cx + rx2*0.55*rr*math.cos(a), cz + ry2*0.55*rr*math.sin(a)
            if ir.random() < 0.5:
                s2 = ir.uniform(0.16, 0.26)
                jc = ir.uniform(-0.08, 0.08)
                rc = tuple(max(0, min(255, int(c*(1.0+jc)))) for c in ROCK)
                tris += cone(ix_, 0.1, iz_, s2, s2*1.2, rc, segs=5)
            else:
                tris += cone(ix_, 0, iz_, 0.11, 0.5, TRUNK, segs=5)
                tris += cone(ix_, 0.45, iz_, 0.28, 0.55, LEAF, segs=7)
                tris += cone(ix_, 0.72, iz_, 0.18, 0.30,
                             tuple(min(255, int(c*1.15)) for c in LEAF), segs=6)
        # 浪蚀礁石：压在水线上的深色岩石，半浸在浪里
        for k2 in range(2):
            a2 = ir.uniform(0, 6.28)
            ox_, oz_ = cx + rx2*0.72*math.cos(a2), cz + ry2*0.72*math.sin(a2)
            s3 = ir.uniform(0.14, 0.24)
            rc2 = tuple(max(0, int(c*0.72)) for c in ROCK)
            tris += cone(ox_, 0.02, oz_, s3, s3*1.1, rc2, segs=5)

    # 海滩杂物：漂木、海藻团与贝壳碎砾，散落在主岛两岸、岛南北滩与大陆沿岸滩带
    WOOD = (0x6E, 0x5C, 0x48); WEED = (0x39, 0x46, 0x2C); SHELL = (0xC8, 0xBE, 0xA8)
    def beach_prop(x, z):
        yaw = dr.uniform(0, math.pi)
        pick = dr.random()
        if pick < 0.38:      # 漂木：斜搁在滩上的枯木，常伴一小截断枝
            ln = dr.uniform(0.7, 1.5)
            wc = tuple(max(0, min(255, int(c*dr.uniform(0.85, 1.12)))) for c in WOOD)
            tris.extend(rot_box(x, z, yaw, 0, 0.045, 0, 0.11, 0.08, ln, wc, 0.02))
            if dr.random() < 0.5:
                tris.extend(rot_box(x + dr.uniform(-0.3, 0.3), z + dr.uniform(-0.3, 0.3),
                            dr.uniform(0, math.pi), 0, 0.035, 0, 0.07, 0.06, 0.4, wc, 0.02))
        elif pick < 0.72:    # 海藻团：贴地深色藻叶三两片
            gc = tuple(max(0, min(255, int(c*dr.uniform(0.8, 1.15)))) for c in WEED)
            for k2 in range(3):
                tris.extend(rot_box(x + dr.uniform(-0.25, 0.25), z + dr.uniform(-0.25, 0.25),
                            dr.uniform(0, math.pi), 0, 0.012, 0,
                            dr.uniform(0.25, 0.5), 0.015, dr.uniform(0.25, 0.5), gc, 0.0))
        else:                # 贝壳碎砾：一小撮浅色细碎
            for k2 in range(4):
                tris.extend(cone(x + dr.uniform(-0.35, 0.35), 0.005, z + dr.uniform(-0.35, 0.35),
                            dr.uniform(0.03, 0.07), 0.03, SHELL, segs=5))
    for k in range(32):      # 主岛东西两岸
        z = dr.uniform(5.5, 34.5)
        x = isl_x0(z) + dr.uniform(0.3, 1.5) if dr.random() < 0.5 \
            else isl_x1(z) - dr.uniform(0.3, 1.5)
        beach_prop(x, z)
    for k in range(18):      # 主岛南北滩
        x = dr.uniform(10, 44)
        z = isl_z0(x) + dr.uniform(0.3, 1.5) if dr.random() < 0.5 \
            else isl_z1(x) - dr.uniform(0.3, 1.5)
        beach_prop(x, z)
    for k in range(13):      # 大陆沿岸滩带
        z = dr.uniform(1.0, 18.0)
        beach_prop(main_x(z) + dr.uniform(0.3, 1.4), z)

    # 远景延伸：东侧接大陆腹地，其余铺深海到地平线（巨三角形会被近平面整体裁掉）
    DEEP = (0x22, 0x46, 0x6E)
    for ax in range(-140, 200, 20):
        for az in range(-120, 160, 20):
            if 0 <= ax < 60 and 0 <= az < 40:
                continue
            p00 = (ax, 0, az); p10 = (ax+20, 0, az)
            p11 = (ax+20, 0, az+20); p01 = (ax, 0, az+20)
            if ax + 10 >= 52.0:
                tris.append((p00, p10, p11, DIRT1, 'ground'))
                tris.append((p00, p11, p01, DIRT1, 'ground'))
            else:
                tris.append((p00, p10, p11, DEEP, 'water'))
                tris.append((p00, p11, p01, DEEP, 'water'))

    # 远山剪影：两重低山脊包住地平线，靠雾吃成淡影（土色/岩色分层）
    mr = random.Random(770728)
    mtn = []
    PAL1 = [(0x86,0x78,0x68), (0x8E,0x80,0x70), (0x7A,0x6E,0x60), (0x94,0x86,0x76)]
    PAL2 = [(0xA0,0x96,0x88), (0xAA,0xA0,0x92), (0x96,0x8C,0x7E)]
    for k in range(14):
        x = -55 + k*15 + mr.uniform(-4, 4)
        mtn += cone(x, 0, -80 - (k % 3) * 10, mr.uniform(10, 20),
                    mr.uniform(6, 14), PAL1[k % 4], segs=7)
    for k in range(9):
        x = -45 + k*20 + mr.uniform(-5, 5)
        mtn += cone(x, 0, -125 - (k % 2) * 12, mr.uniform(18, 30),
                    mr.uniform(12, 22), PAL2[k % 3], segs=7)
    tris += [(a, b, c, col, 'mtn') for (a, b, c, col) in mtn]

    # 投影：顶面沿太阳反方向投到地面 y=0.015
    shadows = []
    for t in tris:
        kind = t[4] if len(t) >= 5 else 'unit'
        if kind != 'unit':
            continue
        n = tri_normal(t)
        if n[1] <= 0.05:
            continue
        if (t[0][1] + t[1][1] + t[2][1]) / 3 <= 0.06:
            continue
        proj = lambda p: (p[0] - SUN[0]*(p[1]/SUN[1]), 0.015,
                          p[2] - SUN[2]*(p[1]/SUN[1]))
        shadows.append((proj(t[0]), proj(t[1]), proj(t[2]), (52, 48, 42), 'shadow'))
    tris.extend(shadows)
    return tris

# ---- 相机与光栅 ----
def normalize(v):
    L = math.sqrt(sum(k*k for k in v)) or 1.0
    return (v[0]/L, v[1]/L, v[2]/L)

SUN = (-0.32, 0.36, -0.55)  # 傍晚低角度夕照：太阳压到西北海面方向
_sunh = math.hypot(SUN[0], SUN[2]) or 1.0
SUNH = (SUN[0]/_sunh, SUN[2]/_sunh)   # 太阳水平方位，用于水面反光带

def tri_normal(t):
    a, b, c = t[0], t[1], t[2]
    u = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
    v = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
    n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    return normalize(n)

def render(scene, eye, target, fov, out_path, label):
    dx, dy, dz = eye[0]-target[0], eye[1]-target[1], eye[2]-target[2]
    L = math.sqrt(dx*dx+dy*dy+dz*dz)
    fwd = normalize((-dx/L, -dy/L, -dz/L))
    right = normalize((-fwd[2], 0, fwd[0]))            # 前向 × 世界上方
    up = (right[1]*fwd[2]-right[2]*fwd[1], right[2]*fwd[0]-right[0]*fwd[2],
          right[0]*fwd[1]-right[1]*fwd[0])
    # 渐变天空（傍晚）：顶部暮蓝紫 → 地平线暖琥珀，落日一侧压光晕
    SKY_TOP, SKY_HZ = (0x5E, 0x66, 0x82), (0xE0, 0xA8, 0x74)
    grad = Image.new('RGB', (1, H))
    gp = grad.load()
    for yy in range(H):
        f = (yy / H) ** 1.5
        gp[0, yy] = tuple(int(SKY_TOP[i] + (SKY_HZ[i]-SKY_TOP[i]) * f) for i in range(3))
    img = grad.resize((W, H))
    px = img.load()
    s = (H/2) / math.tan(fov/2)

    # 夕阳光晕：把太阳方向投到天上，落日位置叠暖色辉光与日轮
    sxw, syw, szw = eye[0] + SUN[0]*420, eye[1] + SUN[1]*420, eye[2] + SUN[2]*420
    vx_, vy_, vz_ = sxw - eye[0], syw - eye[1], szw - eye[2]
    cz_ = vx_*fwd[0] + vy_*fwd[1] + vz_*fwd[2]
    if cz_ > 0:
        cx_ = vx_*right[0] + vy_*right[1] + vz_*right[2]
        cy_ = vx_*up[0] + vy_*up[1] + vz_*up[2]
        gx, gy = W/2 + cx_*s/cz_, H/2 - cy_*s/cz_
        for yy in range(max(0, int(gy-170)), min(H, int(gy+170))):
            for xx in range(max(0, int(gx-170)), min(W, int(gx+170))):
                d2 = (xx-gx)**2 + (yy-gy)**2
                if d2 >= 170*170:
                    continue
                g = max(0.0, 1.0 - d2/(170*170)) ** 1.6
                gd = max(0.0, 1.0 - d2/676.0) ** 2.0
                wt = min(1.0, g*0.40 + gd*0.85)
                o = px[xx, yy]
                px[xx, yy] = tuple(min(255, int(o[i] + (255, 205, 138)[i]*wt)) for i in range(3))

    buckets = {'apron': [], 'ground': [], 'water': [], 'shadow': [], 'unit': []}
    for t in scene:
        kind = t[4] if len(t) >= 5 else 'unit'
        bk = kind if kind in ('apron', 'ground', 'water', 'shadow') else 'unit'
        pts = []
        ok = True
        for p in t[:3]:
            wx, wy, wz = p[0]-eye[0], p[1]-eye[1], p[2]-eye[2]
            cz = wx*fwd[0]+wy*fwd[1]+wz*fwd[2]              # 深度
            cx = wx*right[0]+wy*right[1]+wz*right[2]        # 横向
            cy = wx*up[0]+wy*up[1]+wz*up[2]                 # 纵向
            if cz <= 0.1:
                ok = False; break
            pts.append((W/2 + cx*s/cz, H/2 - cy*s/cz, cz))
        if not ok: continue
        z = sum(p[2] for p in pts)/3
        buckets[bk].append((z, pts, t[3], tri_normal(t), t[:3]))

    gp = GROUND_PHOTO.load() if GROUND_PHOTO is not None else None
    gw, gh = GROUND_PHOTO.size if GROUND_PHOTO is not None else (0, 0)
    sp = SAND_PHOTO.load() if SAND_PHOTO is not None else None
    sw, sh = SAND_PHOTO.size if SAND_PHOTO is not None else (0, 0)

    shadow_mask = set()
    shadow_done = False
    for kind in ('apron', 'ground', 'water', 'shadow', 'unit'):
        if kind == 'unit' and not shadow_done:
            # 软阴影：影子先整体收集，再按 3x3 邻域模糊出半影渐变，边缘不再生硬
            shadow_done = True
            for (sx, sy) in list(shadow_mask):
                acc = 0
                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        if (sx+ox, sy+oy) in shadow_mask:
                            acc += 1
                b = acc/9.0
                o = px[sx, sy]
                px[sx, sy] = tuple(int(o[i]*(1.0-0.60*b) + (52, 48, 42)[i]*0.60*b)
                                   for i in range(3))
        order = sorted(buckets[kind], key=lambda x: -x[0])   # 远到近
        for z, pts, col, n, world in order:
            # 光照：双面漫反射 + 环境项 + 深度衰减
            diff = abs(n[0]*SUN[0] + n[1]*SUN[1] + n[2]*SUN[2])
            depth = min(1.0, z/70)
            lit = 0.44 + 0.58*diff - 0.15*depth   # 傍晚：环境项压低、直射项抬高，明暗对比拉开
            lit = max(0.36, min(1.06, lit))
            # 大气雾（傍晚加重）：远处向暖琥珀地平线混合（远山雾更重，沉进落日天际线）
            fog = min(0.5, max(0.0, (z-14)/110))
            if kind == 'mtn':
                fog = min(0.58, fog*1.4)   # 远山沉进落日天际线，但不糊成沙丘
            if kind == 'water':
                fog *= 0.5                 # 水面少吸暖雾，保住海面蓝调
            (x0, y0, _), (x1, y1, _), (x2, y2, _) = pts
            xs = [x0, x1, x2]; ys = [y0, y1, y2]
            minx, maxx = max(0, int(min(xs))), min(W-1, int(max(xs))+1)
            miny, maxy = max(0, int(min(ys))), min(H-1, int(max(ys))+1)
            area = (x1-x0)*(y2-y0)-(x2-x0)*(y1-y0)
            if abs(area) < 1e-9: continue
            is_shadow = kind == 'shadow'
            textured = kind in ('ground', 'apron', 'water') and gp is not None
            (X0, Y0, Z0), (X1, Y1, Z1), (X2, Y2, Z2) = world
            for yy in range(miny, maxy+1):
                for xx in range(minx, maxx+1):
                    v0 = (x1-x0)*(yy-y0)-(y1-y0)*(xx-x0)
                    v1 = (x2-x1)*(yy-y1)-(y2-y1)*(xx-x1)
                    v2 = (x0-x2)*(yy-y2)-(y0-y2)*(xx-x2)
                    if (v0 >= 0 and v1 >= 0 and v2 >= 0) or (v0 <= 0 and v1 <= 0 and v2 <= 0):
                        if is_shadow:
                            if (xx, yy) in shadow_mask: continue
                            shadow_mask.add((xx, yy))
                            o = px[xx, yy]
                            sc = tuple(min(255, int(c*lit)) for c in col)
                            px[xx, yy] = tuple(int(o[i]*(1-0.62) + sc[i]*0.62) for i in range(3))
                            continue
                        if textured:
                            # 重心坐标 → 世界坐标 → 实拍纹理/程序水面逐像素采样
                            w1 = v1/area; w2 = v2/area; w0 = v0/area
                            wx = w1*X0 + w2*X1 + w0*X2
                            wz = w1*Z0 + w2*Z1 + w0*Z2
                            if kind == 'water':
                                # 水面：流动波纹（沿 x 拉长的流带）+ 近岸沙色过渡 + 深水压暗
                                edge = 1e9
                                if wx < isl_x0(wz): edge = min(edge, isl_x0(wz) - wx)
                                if isl_x1(wz) < wx < main_x(wz):
                                    edge = min(edge, wx - isl_x1(wz), main_x(wz) - wx)
                                if wx <= isl_x1(wx) and wz < isl_z0(wx):
                                    edge = min(edge, isl_z0(wx) - wz)
                                if wx <= isl_x1(wx) and wz > isl_z1(wx):
                                    edge = min(edge, wz - isl_z1(wx))
                                ie_w = islet_e(wx, wz)
                                if 1.0 < ie_w < 2.2:
                                    edge = min(edge, (ie_w - 1.0) * 1.1)
                                flow = wz*2.4 + wx*0.45
                                f = 0.94 + 0.14*math.sin(flow) \
                                        + 0.07*math.sin(flow*2.6 + 1.7) \
                                        + 0.05*math.sin(wx*3.1 - wz*1.8)
                                if ((int(wx*13.7) ^ int(wz*11.3)) & 63) == 0:
                                    f *= 1.26
                                # 深浅分层：浅滩提亮、中段过渡、深海压暗偏墨蓝，界线加噪声打散
                                dn = math.sin(wx*0.31+wz*0.23)*math.sin(wx*0.13-wz*0.41)
                                shallow = min(1.0, max(0.0, edge/5.0 + 0.16*dn))
                                deep_m = min(1.0, max(0.0, (edge-6.0)/12.0))
                                c = tuple(min(255, int(((k*0.78 + 0.22*95)*(0.78+0.26*shallow)*(1.0-0.25*deep_m)
                                          + (0x16,0x33,0x52)[i]*0.25*deep_m)*f*lit))
                                          for i, k in enumerate(WATER))
                                if sp is not None and edge < 1.0:
                                    t = 1.0 - edge   # 1=贴岸
                                    u = min(sw-1, int((wx % 3.5)/3.5*sw))
                                    v = min(sh-1, int((wz % 3.5)/3.5*sh))
                                    sand = sp[u, v]
                                    wet = tuple(min(255, int(s*0.72 + 40)) for s in sand)
                                    c = tuple(int(c[i]*(1-t*0.8) + wet[i]*(t*0.8)) for i in range(3))
                                elif sp is not None and edge < 3.5:
                                    # 浅滩水下沙纹：沙色透过浅水隐约可见，随波纹明暗起伏
                                    st_ = max(0.0, 1.0 - (edge - 1.0) / 2.5)
                                    rip = math.sin(wx*2.2 + wz*1.3)*math.sin(wx*0.9 - wz*2.1)
                                    c = tuple(min(255, max(0, int(c[i]*(1.0 + 0.06*rip)
                                              + (188,172,142)[i]*st_*0.30))) for i in range(3))
                                if edge < 0.45:
                                    # 白浪线：贴岸断续泡沫，随波纹起伏
                                    foam_n = ((int(wx*9.1) ^ int(wz*7.7)) & 7)
                                    ft = max(0.0, 1.0 - edge/0.45) * (0.42 + 0.34*foam_n/7) \
                                                      * (0.7 + 0.3*math.sin(wz*4.3 + wx*0.9))
                                    ft = min(0.72, ft)
                                    c = tuple(int(c[i]*(1-ft) + 243*ft) for i in range(3))
                                elif edge < 1.25:
                                    # 第二道残沫线：拍岸后回撤的稀薄泡沫，断续更碎
                                    foam_n2 = ((int(wx*14.3) ^ int(wz*9.9)) & 15)
                                    ft2 = max(0.0, 1.0 - abs(edge - 0.8) / 0.45) \
                                                        * (0.10 + 0.14*foam_n2/15) \
                                                        * (0.55 + 0.45*math.sin(wz*5.7 + wx*1.3))
                                    ft2 = min(0.30, max(0.0, ft2))
                                    c = tuple(int(c[i]*(1-ft2) + 240*ft2) for i in range(3))
                                # 夕阳碎金：朝太阳方位的水面拉出高光反光带，随波纹碎化
                                vsx_, vsz_ = wx - eye[0], wz - eye[2]
                                vlw = math.hypot(vsx_, vsz_) or 1.0
                                gl = max(0.0, (vsx_/vlw)*SUNH[0] + (vsz_/vlw)*SUNH[1]) ** 9
                                ripple = 0.55 + 0.45*math.sin(wx*3.3 + wz*2.1)
                                gt_ = min(0.36, gl*ripple*0.55)
                                c = tuple(min(255, int(c[i]*(1-gt_) + (255, 218, 158)[i]*gt_))
                                          for i in range(3))
                            else:
                                # 岸缘距离场：沙土由硬切带改为噪声起伏的渐变过渡
                                db = 1e9
                                if isl_x0(wz) <= wx <= isl_x1(wz) and isl_z0(wx) <= wz <= isl_z1(wx):
                                    db = min(wx-isl_x0(wz), isl_x1(wz)-wx, wz-isl_z0(wx), isl_z1(wx)-wz)
                                elif wx >= main_x(wz):
                                    db = wx - main_x(wz)
                                ie_g = islet_e(wx, wz)
                                if ie_g < 1.5:
                                    db = min(db, (1.5 - ie_g) * 1.2)
                                edge_noise = 0.5*math.sin(wx*0.83+2.1)*math.sin(wz*0.71-1.3) \
                                             + 0.3*math.sin(wx*1.9-wz*1.4)
                                bt = max(0.0, min(1.0, (db + edge_noise - 1.2) / 1.5))
                                if sp is not None:
                                    # 沙滩层：两层实拍沙滩采样
                                    u1 = min(sw-1, int((wx % 3.5)/3.5*sw))
                                    v1 = min(sh-1, int((wz % 3.5)/3.5*sh))
                                    u2 = min(sw-1, int(((wx+1.7) % 9.0)/9.0*sw))
                                    v2 = min(sh-1, int(((wz+4.1) % 9.0)/9.0*sh))
                                    sA, sB = sp[u1, v1], sp[u2, v2]
                                    c_sand = tuple((sA[i]*2 + sB[i]) // 3 for i in range(3))
                                else:
                                    c_sand = (0xB8, 0xA8, 0x88)
                                if gp is not None:
                                    u1 = min(gw-1, int((wx % 12.0)/12.0*gw))
                                    v1 = min(gh-1, int((wz % 12.0)/12.0*gh))
                                    u2 = min(gw-1, int(((wx+5.3) % 29.0)/29.0*gw))
                                    v2 = min(gh-1, int(((wz+11.8) % 29.0)/29.0*gh))
                                    gA, gB = gp[u1, v1], gp[u2, v2]
                                    c_dirt = tuple((gA[i]*2 + gB[i]) // 3 for i in range(3))
                                else:
                                    c_dirt = DIRT1 if (gx0_ := int(wx)) is not None else DIRT1
                                # 沙→土渐变混合，渐变带再叠干湿色相扰动
                                c3 = tuple(int(c_dirt[i]*bt + c_sand[i]*(1-bt)) for i in range(3))
                                # 小岛水线浪蚀：贴水一圈被浪打湿的深色带
                                if 0.55 < ie_g < 1.5:
                                    wet_t = max(0.0, 1.0 - abs(ie_g - 1.0) / 0.5) * 0.45
                                    c3 = tuple(int(c3[i]*(1-wet_t) + (0x5E,0x58,0x4E)[i]*wet_t) for i in range(3))
                                moist = 0.93 + 0.09*math.sin(wx*0.37+wz*0.29) \
                                        + 0.05*math.sin(wx*1.3-wz*0.9)
                                macro = 0.90 + 0.11*math.sin(wx*0.21+1.3)*math.sin(wz*0.17+0.6) \
                                        + 0.06*math.sin(wx*0.53-wz*0.41) \
                                        + 0.04*math.sin(wx*1.7+wz*2.3)
                                jit = 1.0 + ((xx*xx*3 + yy*yy*7) % 7 - 3) * 0.006
                                c = tuple(min(255, int(k*jit*macro*moist*lit)) for k in c3)
                                # 傍晚暖调：滩土整体偏暖，太阳背光侧留冷灰
                                WARM_G = (1.07, 1.00, 0.88)
                                c = tuple(min(255, int(c[i]*WARM_G[i])) for i in range(3))
                            if fog > 0:
                                c = tuple(int(k + (SKY_HZ[i]-k)*fog) for i, k in enumerate(c))
                            px[xx, yy] = c
                            continue
                        base = tuple(min(255, int(c*lit)) for c in col)
                        # 单位材质分层：贴地环境光遮蔽 + 边缘冷光 + 向阳高光
                        if kind == 'unit':
                            cxw = (X0+X1+X2)/3; cyw = (Y0+Y1+Y2)/3; czw = (Z0+Z1+Z2)/3
                            vx, vy, vz = eye[0]-cxw, eye[1]-cyw, eye[2]-czw
                            vl = math.sqrt(vx*vx+vy*vy+vz*vz) or 1.0
                            vd = abs(n[0]*vx/vl + n[1]*vy/vl + n[2]*vz/vl)
                            rim = max(0.0, 1.0 - vd) ** 2.4
                            ao = min(1.0, 0.70 + 0.30*min(1.0, cyw/1.4))
                            base = tuple(min(255, int(k*ao)) for k in base)
                            sky_ref = (0xE4, 0xB4, 0x8E)   # 傍晚：边缘反射暖天光
                            base = tuple(min(255, int(k + (sky_ref[i]-k)*rim*0.50))
                                         for i, k in enumerate(base))
                            spec = max(0.0, diff - 0.72) * 1.3
                            base = tuple(min(255, int(k + (255-k)*spec)) for k in base)
                            # 金属漆磨损颗粒：低频污渍 + 高频颗粒，打散大块面色板
                            wxg = (X0+X1+X2)/3 + math.sin((Y0+Y1+Y2)*3.1)*0.3
                            wear = 0.92 + 0.08*math.sin(cxw*2.7+czw*1.9) \
                                       + 0.05*math.sin(cxw*8.1-czw*6.3)
                            grain = 1.0 + ((xx*xx*5 + yy*yy*13 + int(cxw*7.3)*17 + int(czw*3.1)*29) % 11 - 5) * 0.013
                            base = tuple(min(255, max(0, int(k*wear*grain))) for k in base)
                            # 傍晚暖调：装备漆面迎光侧偏暖，压低整体亮度
                            WARM_U = (1.09, 0.99, 0.86)
                            base = tuple(min(255, max(0, int(base[i]*WARM_U[i]))) for i in range(3))
                            # 下缘溅泥：贴地面越近泥色越重，模拟野战行驶沉积
                            if cyw < 0.5:
                                mud_t = max(0.0, (0.5 - cyw) / 0.5) * 0.42
                                MUD = (0x6E, 0x5C, 0x44)
                                base = tuple(int(base[i]*(1-mud_t) + MUD[i]*mud_t) for i in range(3))
                        if fog > 0:
                            base = tuple(int(b + (SKY_HZ[i]-b)*fog) for i, b in enumerate(base))
                        px[xx, yy] = base
    img.save(out_path)
    print('saved', out_path, label)

scene = build_scene()
# 视角一：RTS 高角俯瞰（类似玩家镜头）
render(scene, (22, 26, 52), (28, 0, 8), math.radians(58), f'{ROOT}/proxy_view_wide.png', 'wide')
# 视角二：贴近地面近景（看单位观感）
render(scene, (13, 4.5, 20), (8, 1.2, 4), math.radians(52), f'{ROOT}/proxy_view_close.png', 'close')
render(scene, (30, 2.0, 18.6), (29.8, 0.5, 5.0), math.radians(50), f'{ROOT}/proxy_view_prc.png', 'prc')
# 视角四：海峡火力线（阶段一海空准备——纵队+双机+对岸弹着成列）
render(scene, (41, 8.5, 22), (57, 0.3, 15), math.radians(55), f'{ROOT}/proxy_view_strait.png', 'strait')
# 视角五：掠海侦察线（阶段一第二班——三机波次贴海低空+水面机影+下洗波纹）
render(scene, (41.5, 7.0, 30.5), (49.0, 0.5, 24.0), math.radians(50), f'{ROOT}/proxy_view_helo.png', 'helo')
# 视角六：港湾驻泊线（编队驻泊细节——三舰靠帮成列+护舷垫+锚浮标+码头哨兵）
render(scene, (0.2, 5.5, 22.5), (4.8, 0.2, 13.8), math.radians(52), f'{ROOT}/proxy_view_anchorage.png', 'anchorage')
