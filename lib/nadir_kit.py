"""Kit de construction Roblox : scène (liste d'instances), repères locaux, écriture .rbxlx et .json (pour les aperçus Blender).
Repère Roblox : X = est, Y = haut, Z = sud (Z = -z du plan). Les tailles sont en studs."""
import math, json, base64, random

MAT = dict(Plastic=256, SmoothPlastic=272, Neon=288, Wood=512, WoodPlanks=528, Marble=784, Slate=800, Concrete=816, Granite=832,
           Brick=848, Pebble=864, Cobblestone=880, Rock=896, CorrodedMetal=1040, DiamondPlate=1056, Foil=1072, Metal=1088,
           Grass=1280, Sand=1296, Fabric=1312, Ice=1536, Glass=1568)
FACE = dict(Right=0, Top=1, Back=2, Left=3, Bottom=4, Front=5)

def rot_y(a):
    c, s = math.cos(a), math.sin(a); return ((c, 0, s), (0, 1, 0), (-s, 0, c))
def rot_x(a):
    c, s = math.cos(a), math.sin(a); return ((1, 0, 0), (0, c, -s), (0, s, c))
def rot_z(a):
    c, s = math.cos(a), math.sin(a); return ((c, -s, 0), (s, c, 0), (0, 0, 1))
def mm(A, B): return tuple(tuple(sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)) for i in range(3))
def mv(A, v): return tuple(sum(A[i][k]*v[k] for k in range(3)) for i in range(3))
I3 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
def norm(v): l = math.sqrt(sum(x*x for x in v)) or 1; return tuple(x/l for x in v)
def cross(a, b): return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])
def axis_x_to(d):
    """rotation dont l'axe X local pointe vers d (les cylindres Roblox sont orientés selon X)"""
    x = norm(d); up = (0, 1, 0) if abs(x[1]) < 0.95 else (1, 0, 0)
    z = norm(cross(x, up)); y = cross(z, x)
    return tuple((x[i], y[i], z[i]) for i in range(3))

class Scene:
    def __init__(s, seed=4):
        s.items = []; s.rng = random.Random(seed); s.folders = set()
    def add(s, folder, cls, name, size, pos, R=I3, mat='SmoothPlastic', col=(200, 200, 200), tr=0.0, refl=0.0, cc=True,
            shadow=True, shape=None, children=None, tags=None, **extra):
        it = dict(f=folder, cls=cls, n=name, s=[round(v, 3) for v in size], p=[round(v, 3) for v in pos], R=R, m=mat, c=col,
                  t=tr, r=refl, cc=cc, sh=shadow, shape=shape, ch=children or [], tags=tags or [])
        it.update(extra); s.items.append(it); s.folders.add(folder); return it

class Frame:
    """repère local : origine (monde), rotation R (colonnes = axes locaux dans le monde)"""
    def __init__(s, sc, folder, pos, R=I3):
        s.sc, s.folder, s.pos, s.R = sc, folder, tuple(pos), R
    def w(s, c): v = mv(s.R, c); return (s.pos[0] + v[0], s.pos[1] + v[1], s.pos[2] + v[2])
    def sub(s, c, yaw=0.0, R=None):
        return Frame(s.sc, s.folder, s.w(c), mm(s.R, R if R is not None else rot_y(yaw)))
    def box(s, c, size, mat='SmoothPlastic', col=(200, 200, 200), name='Part', R=None, **kw):
        if min(size) <= 0.01: return None
        return s.sc.add(s.folder, 'Part', name, size, s.w(c), mm(s.R, R) if R else s.R, mat, col, **kw)
    def wedge(s, c, size, mat='SmoothPlastic', col=(200, 200, 200), name='Wedge', R=None, **kw):
        return s.sc.add(s.folder, 'WedgePart', name, size, s.w(c), mm(s.R, R) if R else s.R, mat, col, **kw)
    def cyl(s, c, length, diam, axis='y', mat='Metal', col=(150, 150, 150), name='Cyl', **kw):
        d = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}[axis] if isinstance(axis, str) else axis
        R = mm(s.R, axis_x_to(d))
        return s.sc.add(s.folder, 'Part', name, (length, diam, diam), s.w(c), R, mat, col, shape='Cylinder', **kw)
    def ball(s, c, diam, mat='SmoothPlastic', col=(200, 200, 200), name='Ball', **kw):
        return s.sc.add(s.folder, 'Part', name, (diam, diam, diam), s.w(c), s.R, mat, col, shape='Ball', **kw)
    def pipe(s, a, b, diam, mat='Metal', col=(140, 140, 140), name='Tuyau', **kw):
        a, b = s.w(a), s.w(b); d = (b[0] - a[0], b[1] - a[1], b[2] - a[2]); L = math.sqrt(sum(x*x for x in d))
        if L < 0.05: return None
        return s.sc.add(s.folder, 'Part', name, (L, diam, diam), ((a[0] + b[0])/2, (a[1] + b[1])/2, (a[2] + b[2])/2), axis_x_to(d), mat, col, shape='Cylinder', **kw)
    def light(s, c, kind='PointLight', col=(255, 255, 255), brightness=1.0, rng=16, face='Bottom', angle=90, shadows=True,
              enabled=True, tags=None, part_size=(0.2, 0.2, 0.2), part_mat='SmoothPlastic', part_col=(255, 255, 255), part_tr=1.0, name='Lumiere'):
        L = dict(cls=kind, Brightness=brightness, Color=col, Range=rng, Shadows=shadows, Enabled=enabled)
        if kind != 'PointLight': L.update(Face=FACE[face], Angle=angle)
        return s.box(c, part_size, part_mat, part_col, name=name, tr=part_tr, cc=False, shadow=False, children=[L], tags=tags or [])
    def text(s, c, size, txt, col=(20, 20, 20), bg=(235, 235, 225), face='Front', mat='SmoothPlastic', name='Panneau', ppu=40, txtcol=None, **kw):
        g = dict(cls='SurfaceGui', Face=FACE[face], PixelsPerStud=ppu, Text=txt, TextColor=txtcol or col)
        return s.box(c, size, mat, bg, name=name, children=[g], **kw)

# ---------------------------------------------------------------- écriture .rbxlx
_ref = [0]
def _r(): _ref[0] += 1; return f'RBX{_ref[0]:07d}'
def _esc(t): return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def _c3u8(c): return str(0xFF000000 | (int(c[0]) << 16) | (int(c[1]) << 8) | int(c[2]))
def _cf(p, R):
    return ('<X>%g</X><Y>%g</Y><Z>%g</Z>' % tuple(p)) + ''.join(f'<R{i}{j}>{R[i][j]:.6g}</R{i}{j}>' for i in range(3) for j in range(3))
def _c3(c): return f'<R>{c[0]/255:.4g}</R><G>{c[1]/255:.4g}</G><B>{c[2]/255:.4g}</B>'
def _tags(t): return base64.b64encode('\x00'.join(t).encode()).decode()

def _child_xml(ch):
    k = ch['cls']; out = [f'<Item class="{k}" referent="{_r()}"><Properties>']
    if k in ('PointLight', 'SpotLight', 'SurfaceLight'):
        out.append(f'<float name="Brightness">{ch["Brightness"]}</float><Color3 name="Color">{_c3(ch["Color"])}</Color3>'
                   f'<float name="Range">{ch["Range"]}</float><bool name="Shadows">{str(ch["Shadows"]).lower()}</bool><bool name="Enabled">{str(ch["Enabled"]).lower()}</bool>')
        if k != 'PointLight': out.append(f'<token name="Face">{ch["Face"]}</token><float name="Angle">{ch["Angle"]}</float>')
        out.append('</Properties></Item>'); return ''.join(out)
    if k == 'SurfaceGui':
        out.append(f'<string name="Name">Texte</string><token name="Face">{ch["Face"]}</token><token name="SizingMode">1</token>'
                   f'<float name="PixelsPerStud">{ch["PixelsPerStud"]}</float><token name="LightInfluence">1</token></Properties>')
        out.append(f'<Item class="TextLabel" referent="{_r()}"><Properties><string name="Name">Libelle</string>'
                   '<UDim2 name="Size"><XS>1</XS><XO>0</XO><YS>1</YS><YO>0</YO></UDim2><float name="BackgroundTransparency">1</float>'
                   f'<string name="Text">{_esc(ch["Text"])}</string><Color3 name="TextColor3">{_c3(ch["TextColor"])}</Color3>'
                   '<bool name="TextScaled">true</bool><bool name="TextWrapped">true</bool><token name="Font">4</token></Properties></Item></Item>')
        return ''.join(out)
    if k == 'ParticleEmitter':
        p = ch
        out.append(f'<Content name="Texture"><url>{p.get("Texture", "rbxasset://textures/particles/sparkles_main.dds")}</url></Content>'
                   f'<float name="Rate">{p["Rate"]}</float><NumberRange name="Lifetime">{p["Lifetime"][0]} {p["Lifetime"][1]} </NumberRange>'
                   f'<NumberRange name="Speed">{p["Speed"][0]} {p["Speed"][1]} </NumberRange>'
                   f'<NumberSequence name="Size">0 {p["Size"]} 0 1 {p["Size"]} 0 </NumberSequence>'
                   f'<NumberSequence name="Transparency">0 {p["Transp"][0]} 0 1 {p["Transp"][1]} 0 </NumberSequence>'
                   f'<ColorSequence name="Color">0 {p["Color"][0]/255:.3g} {p["Color"][1]/255:.3g} {p["Color"][2]/255:.3g} 0 1 {p["Color"][0]/255:.3g} {p["Color"][1]/255:.3g} {p["Color"][2]/255:.3g} 0 </ColorSequence>'
                   f'<Vector3 name="Acceleration"><X>{p["Acc"][0]}</X><Y>{p["Acc"][1]}</Y><Z>{p["Acc"][2]}</Z></Vector3>'
                   f'<Vector2 name="SpreadAngle"><X>{p["Spread"]}</X><Y>{p["Spread"]}</Y></Vector2><float name="LightEmission">{p.get("Emission", 0)}</float>'
                   f'<token name="EmissionDirection">{p.get("Dir", 1)}</token></Properties></Item>')
        return ''.join(out)
    return ''

def _part_xml(it):
    cls = it['cls']
    p = [f'<Item class="{cls}" referent="{_r()}"><Properties>',
         f'<string name="Name">{_esc(it["n"])}</string><bool name="Anchored">true</bool>',
         f'<CoordinateFrame name="CFrame">{_cf(it["p"], it["R"])}</CoordinateFrame>',
         f'<Vector3 name="size"><X>{it["s"][0]}</X><Y>{it["s"][1]}</Y><Z>{it["s"][2]}</Z></Vector3>',
         f'<token name="Material">{MAT[it["m"]]}</token><Color3uint8 name="Color3uint8">{_c3u8(it["c"])}</Color3uint8>',
         f'<float name="Transparency">{it["t"]}</float><float name="Reflectance">{it["r"]}</float>',
         f'<bool name="CanCollide">{str(it["cc"]).lower()}</bool><bool name="CanTouch">false</bool><bool name="CastShadow">{str(it["sh"]).lower()}</bool>',
         ''.join(f'<token name="{f}Surface">0</token>' for f in ('Top', 'Bottom', 'Left', 'Right', 'Front', 'Back'))]
    if not it['cc']: p.append('<bool name="CanQuery">false</bool>')
    if it.get('shape'): p.append(f'<token name="shape">{dict(Ball=0, Block=1, Cylinder=2)[it["shape"]]}</token>')
    if it['tags']: p.append(f'<BinaryString name="Tags">{_tags(it["tags"])}</BinaryString>')
    if cls == 'SpawnLocation': p.append('<bool name="Neutral">true</bool><int name="Duration">0</int>')
    p.append('</Properties>'); p += [_child_xml(c) for c in it['ch']]; p.append('</Item>')
    return ''.join(p)

def write_rbxlx(sc, path, lighting, scripts=(), rs_values=()):
    """lighting : dict de propriétés + effets ; scripts : [(nom, source, parent 'ServerScriptService'|'Workspace')]"""
    tree = {}
    for it in sc.items:
        node = tree
        for name in it['f'].split('/'): node = node.setdefault(name, {})
        node.setdefault('__items', []).append(it)
    def folder_xml(name, node):
        out = [f'<Item class="Folder" referent="{_r()}"><Properties><string name="Name">{_esc(name)}</string></Properties>']
        for k, v in node.items():
            if k != '__items': out.append(folder_xml(k, v))
        out += [_part_xml(it) for it in node.get('__items', [])]
        out.append('</Item>'); return ''.join(out)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" version="4">\n')
        f.write(f'<Item class="Workspace" referent="{_r()}"><Properties><string name="Name">Workspace</string>'
                '<bool name="StreamingEnabled">true</bool><float name="Gravity">196.2</float></Properties>\n')
        for k, v in tree.items(): f.write(folder_xml(k, v) + '\n')
        for name, src, parent in scripts:
            if parent == 'Workspace':
                f.write(f'<Item class="Script" referent="{_r()}"><Properties><string name="Name">{name}</string><ProtectedString name="Source"><![CDATA[{src}]]></ProtectedString></Properties></Item>\n')
        f.write('</Item>\n')
        L = lighting
        f.write(f'<Item class="Lighting" referent="{_r()}"><Properties><string name="Name">Lighting</string>'
                f'<token name="Technology">4</token><Color3 name="Ambient">{_c3(L["ambient"])}</Color3><float name="Brightness">{L["brightness"]}</float>'
                f'<Color3 name="OutdoorAmbient">{_c3(L["outdoor"])}</Color3><string name="TimeOfDay">00:00:00</string><float name="ClockTime">0</float>'
                f'<float name="EnvironmentDiffuseScale">{L.get("diffuse", 0.3)}</float><float name="EnvironmentSpecularScale">{L.get("specular", 0.6)}</float>'
                f'<bool name="GlobalShadows">true</bool><float name="ExposureCompensation">{L.get("exposure", 0)}</float>'
                f'<Color3 name="FogColor">{_c3(L["fog"])}</Color3><float name="FogEnd">{L.get("fog_end", 300)}</float><float name="FogStart">0</float></Properties>')
        a = L['atmos']
        f.write(f'<Item class="Atmosphere" referent="{_r()}"><Properties><string name="Name">EauProfonde</string><float name="Density">{a["density"]}</float>'
                f'<float name="Offset">{a["offset"]}</float><Color3 name="Color">{_c3(a["color"])}</Color3><Color3 name="Decay">{_c3(a["decay"])}</Color3>'
                f'<float name="Glare">0</float><float name="Haze">{a["haze"]}</float></Properties></Item>')
        cc = L['cc']
        f.write(f'<Item class="ColorCorrectionEffect" referent="{_r()}"><Properties><string name="Name">Etalonnage</string><float name="Brightness">{cc["brightness"]}</float>'
                f'<float name="Contrast">{cc["contrast"]}</float><float name="Saturation">{cc["saturation"]}</float><Color3 name="TintColor">{_c3(cc["tint"])}</Color3></Properties></Item>')
        b = L['bloom']
        f.write(f'<Item class="BloomEffect" referent="{_r()}"><Properties><string name="Name">Halo</string><float name="Intensity">{b["intensity"]}</float>'
                f'<float name="Size">{b["size"]}</float><float name="Threshold">{b["threshold"]}</float></Properties></Item>')
        f.write('</Item>\n')
        f.write(f'<Item class="ReplicatedStorage" referent="{_r()}"><Properties><string name="Name">ReplicatedStorage</string></Properties>')
        for name, val in rs_values:
            f.write(f'<Item class="BoolValue" referent="{_r()}"><Properties><string name="Name">{name}</string><bool name="Value">{str(val).lower()}</bool></Properties></Item>')
        f.write('</Item>\n')
        f.write(f'<Item class="ServerScriptService" referent="{_r()}"><Properties><string name="Name">ServerScriptService</string></Properties>')
        for name, src, parent in scripts:
            if parent == 'ServerScriptService':
                f.write(f'<Item class="Script" referent="{_r()}"><Properties><string name="Name">{name}</string><ProtectedString name="Source"><![CDATA[{src}]]></ProtectedString></Properties></Item>')
        f.write('</Item>\n</roblox>\n')

def write_json(sc, path):
    """version compacte pour les aperçus Blender"""
    out = []
    for it in sc.items:
        d = dict(k=it['cls'], s=it['s'], p=it['p'], R=[list(r) for r in it['R']], m=it['m'], c=list(it['c']), t=it['t'], sh=it.get('shape'), f=it['f'], n=it['n'])
        L = [c for c in it['ch'] if c['cls'] in ('PointLight', 'SpotLight', 'SurfaceLight')]
        if L: d['L'] = [dict(k=l['cls'], b=l['Brightness'], c=list(l['Color']), r=l['Range'], e=l['Enabled'], face=l.get('Face'), a=l.get('Angle')) for l in L]
        g = [c for c in it['ch'] if c['cls'] == 'SurfaceGui']
        if g: d['txt'] = g[0]['Text']
        if it['tags']: d['tags'] = it['tags']
        out.append(d)
    json.dump(out, open(path, 'w'), separators=(',', ':'))
