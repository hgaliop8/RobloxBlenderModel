--[[ THE WITNESS — gestes (ModuleScript, ReplicatedStorage > Witness).
Calculs partagés par le corps animé (WitnessCorps) :
  - la chute du plafond en trois temps (décrochage, chute libre, atterrissage) ;
  - le cabrage pendant une saisie ;
  - l'enroulement d'un bras le long d'un chemin (hélice autour du cou, appui au sol) : chaque os est tourné pour que
    l'articulation suivante tombe sur le chemin, du haut du bras jusqu'à la pointe.
Repère du modèle : +X devant, +Y dessus, Z sur le côté. Les os des bras sont orientés le long de leur axe Y local. ]]
local G = {}

local function lisse(a) a = math.clamp(a, 0, 1); return a * a * (3 - 2 * a) end
G.lisse = lisse

G.DECROCHE_MAX = 1.2          -- angle (rad) dont l'avant pend pendant un décrochage complet (0,3 s)
G.PIVOT_ARRIERE = Vector3.new(-2.2, 0, 0)   -- là où les bras arrière tiennent encore au plafond
G.CABRE_ANGLE, G.CABRE_HAUTEUR = 0.55, 1.0  -- saisie : elle se dresse sur ses bras arrière
G.CABRE_PIVOT = Vector3.new(-1.8, 0, 0)

local function autourPivot(p: Vector3, a: number): CFrame
	return CFrame.new(p) * CFrame.Angles(0, 0, a) * CFrame.new(-p)
end

--[[ chute du plafond. e = temps depuis le début, d = durée du décrochage, tf = durée de la chute libre, g = gravité,
atterr = durée de l'atterrissage. Renvoie : repère du modèle (à appliquer après l'orientation de la racine), distance
déjà tombée (nil à l'atterrissage), phase, avancement de la phase (0..1), temps depuis l'impact ]]
function G.chute(e: number, d: number, tf: number, g: number, atterr: number): (CFrame, number?, string, number, number)
	local aMax = G.DECROCHE_MAX * math.min(1, d / 0.3)
	local retourne = CFrame.Angles(math.pi, 0, 0)
	if e < d then
		local h = lisse(e / math.max(d, 1e-3))
		return retourne * autourPivot(G.PIVOT_ARRIERE, aMax * h), 0, "decroche", h, 0
	elseif e < d + tf then
		local a = e - d; local u = a / tf
		local s = lisse(math.min(1, u * 1.15))                 -- elle s'est remise à l'endroit juste avant de toucher le sol
		return (retourne * autourPivot(G.PIVOT_ARRIERE, aMax)):Lerp(CFrame.identity, s), 0.5 * g * a * a, "chute", u, 0
	end
	local tau = e - d - tf
	local y = -0.45 * math.sin(math.pi * math.min(tau / 0.2, 1)) * math.exp(-4 * tau)       -- le corps s'écrase puis remonte
	local bascule = -0.12 * math.sin(math.pi * math.min(tau / 0.25, 1))                      -- l'avant touche en premier
	return CFrame.new(0, y, 0) * CFrame.Angles(0, 0, bascule), nil, "atterrit", math.min(1, tau / atterr), tau
end

-- cabrage pendant une saisie (tt = temps depuis la saisie)
function G.cabrer(tt: number): CFrame
	local a = lisse(tt / 0.5)
	return CFrame.new(0, G.CABRE_HAUTEUR * a, 0) * autourPivot(G.CABRE_PIVOT, G.CABRE_ANGLE * a)
end

local function bezier(a: Vector3, b: Vector3, c: Vector3, d: Vector3, n: number, pts: { Vector3 })
	for i = 1, n do
		local u = i / n; local v = 1 - u
		table.insert(pts, a * (v * v * v) + b * (3 * v * v * u) + c * (3 * v * u * u) + d * (u * u * u))
	end
end

--[[ chemin d'un bras qui s'enroule autour d'un cylindre (cou ou torse) :
B = départ du bras, N = centre du cou, U = axe du cou, f = direction horizontale du cou vers elle, r = rayon,
h0 = décalage en hauteur, sens = +1 ou -1 (côté du bras), tours = nombre de tours au maximum ]]
function G.cheminEnroule(B: Vector3, N: Vector3, U: Vector3, f: Vector3, r: number, h0: number, sens: number, tours: number): { Vector3 }
	local l = U:Cross(f).Unit
	local pas = 0.3                                         -- montée par tour
	local function P(th: number): Vector3
		return N + U * (h0 + pas * math.abs(th) / (2 * math.pi)) + (f * math.cos(th) + l * math.sin(th)) * r
	end
	local th0 = sens * 0.75                                 -- elle arrive par l'avant, de son côté
	local E = P(th0)
	local tangente = (P(th0 + sens * 0.05) - E).Unit
	local pts = { B }
	local dehors = Vector3.new(B.X - N.X, 0, B.Z - N.Z)
	dehors = dehors.Magnitude > 1e-3 and dehors.Unit or f
	bezier(B, B + (E - B) * 0.3 + dehors * 0.5 + U * 0.4, E - tangente * 1.1, E, 10, pts)
	local n = math.ceil(tours * 24)
	for i = 1, n do table.insert(pts, P(th0 + sens * (i / 24) * 2 * math.pi)) end
	return pts
end

-- chemin d'un bras d'appui : il descend vers un point du sol puis s'y étale
function G.cheminSol(B: Vector3, dir: Vector3, Fpt: Vector3, haut: Vector3): { Vector3 }
	local pts = { B }
	bezier(B, B + dir * 1.4 + haut * 0.6, Fpt + haut * 1.4, Fpt, 10, pts)
	table.insert(pts, Fpt + dir * 2); table.insert(pts, Fpt + dir * 5)
	return pts
end

-- articulations le long du chemin : J[j] = bout de l'os j, à la distance L[j] du bout précédent
function G.articulations(base: Vector3, pts: { Vector3 }, L: { number }): { Vector3 }
	local J = {}
	local cur = base; local i = 1
	for j = 1, #L do
		local Lj = L[j]; local trouve: Vector3? = nil
		while i < #pts do
			local a, b = pts[i], pts[i + 1]
			local d = b - a; local m = a - cur
			local A = d:Dot(d); local Bq = 2 * m:Dot(d); local Cq = m:Dot(m) - Lj * Lj
			local disc = Bq * Bq - 4 * A * Cq
			if A > 1e-9 and disc >= 0 then
				local u = (-Bq + math.sqrt(disc)) / (2 * A)
				if u >= 0 and u <= 1 then trouve = a + d * u; break end
			end
			i += 1
		end
		if not trouve then
			local n = #pts
			local dir = n >= 2 and (pts[n] - pts[n - 1]) or Vector3.new(1, 0, 0)
			trouve = cur + (dir.Magnitude > 1e-6 and dir.Unit or Vector3.new(1, 0, 0)) * Lj
		end
		J[j] = trouve :: Vector3; cur = trouve :: Vector3
	end
	return J
end

--[[ oriente une chaîne d'os vers les articulations J. chaine.os[j] = os, chaine.axe[j] = axe de l'os dans son repère ;
parent = repère monde du parent du premier os ; poids[j] = mélange entre la pose actuelle (0) et la pose ajustée (1) ]]
function G.orienter(chaine, parent: CFrame, J: { Vector3 }, poids: { number })
	local cf = parent
	for j, b in ipairs(chaine.os) do
		local repos = cf * b.CFrame
		local v = J[j] - repos.Position
		local T = b.Transform
		if v.Magnitude > 1e-4 then
			local dirL = repos:VectorToObjectSpace(v.Unit)
			local axe = chaine.axe[j]
			local c = axe:Cross(dirL)
			local ang = math.acos(math.clamp(axe:Dot(dirL), -1, 1))
			local ajuste = c.Magnitude > 1e-6 and CFrame.fromAxisAngle(c.Unit, ang) or CFrame.identity
			T = T:Lerp(ajuste, poids[j] or 1)
		end
		b.Transform = T
		cf = repos * T
	end
end

-- ================================================================ marche
--[[ Au pas (plafond, sol) : chaque bras a un « pied » collé à la surface ; le corps avance entre ses bras, et quand un pied
est trop loin de sa place, son groupe (un bras sur deux) se décolle et se repose plus loin, en avance sur le corps.
En course rapide, les bras se rassemblent derrière elle en faisceau, avec une seule ondulation commune. ]]
G.MARCHE = {
	rayon = 4.1,          -- distance du centre à laquelle chaque bras se pose
	seuil = 1.5,          -- écart qui déclenche un pas (studs)
	seuil_repos = 0.6,    -- à l'arrêt, les pieds se replacent proprement
	avance = 1.5,         -- le pied se repose en avance de 1,5 × (vitesse × durée du pas)
	anticipation = 0.15,  -- s : la place visée tient compte de la vitesse
	course_debut = 16, course_plein = 22,   -- studs/s : passage de la marche à la course en faisceau
}

function G.nouvelleMarche()
	return { pieds = {} :: { [number]: Vector3 }, air = {} :: { [number]: any }, dernier = 1 }
end

local function surPlan(p: Vector3, origine: Vector3, haut: Vector3): Vector3
	return p - haut * (p - origine):Dot(haut)
end

-- met à jour les pieds. cf = repère affiché du modèle, dirs[k] = direction du bras k (repère du modèle), vel = vitesse (monde)
-- surface (facultatif) : fonction qui ramène un point sur la vraie surface (coin sol/mur/plafond pendant une escalade)
-- glisse (facultatif) : en course, les pieds suivent leur place idéale sans se poser (ils repartiront de là en ralentissant)
function G.majMarche(m, t: number, cf: CFrame, dirs: { [number]: Vector3 }, vel: Vector3, surface: ((Vector3) -> Vector3)?, glisse: boolean?)
	local M = G.MARCHE
	local haut = cf.UpVector; local origine = cf.Position
	vel = vel - haut * vel:Dot(haut)
	local v = vel.Magnitude
	local ideal = {}
	for k, d in pairs(dirs) do
		ideal[k] = surPlan(cf:PointToWorldSpace(d * M.rayon), origine, haut) + vel * M.anticipation
		if surface then ideal[k] = surface(ideal[k]) end
		local p = m.pieds[k]
		if not p or (p - ideal[k]).Magnitude > 13 or (not surface and math.abs((p - origine):Dot(haut)) > 1.5) then
			m.pieds[k] = ideal[k]; m.air[k] = nil                -- nouveau plan (chute, changement de surface) : on repart propre
		end
	end
	if glisse then
		for k in pairs(dirs) do m.pieds[k] = ideal[k] end
		m.air = {}
		return
	end
	for k, a in pairs(m.air) do
		if t - a.t0 >= a.duree then m.pieds[k] = a.fin; m.air[k] = nil end
	end
	if next(m.air) ~= nil then return end
	local seuil = v > 1 and M.seuil or M.seuil_repos
	local ecarts = { 0, 0 }
	for k in pairs(dirs) do
		local g = (k % 2) + 1
		ecarts[g] = math.max(ecarts[g], (m.pieds[k] - ideal[k]).Magnitude)
	end
	local g
	if ecarts[1] > seuil and ecarts[2] > seuil then g = (m.dernier == 1) and 2 or 1
	elseif ecarts[1] > seuil then g = 1 elseif ecarts[2] > seuil then g = 2 end
	if not g then return end
	m.dernier = g
	local duree = math.clamp(0.3 - v * 0.005, 0.18, 0.3)
	for k in pairs(dirs) do
		if (k % 2) + 1 == g then
			local av = vel * duree * M.avance
			if av.Magnitude > 3.5 then av = av.Unit * 3.5 end                 -- pas plus long que 3,5 studs d'avance
			local fin = ideal[k] + av
			if surface then fin = surface(fin) end
			if (m.pieds[k] - fin).Magnitude > 0.3 then
				m.air[k] = { t0 = t, duree = duree, debut = m.pieds[k], fin = fin, hauteur = 0.8 + v * 0.025 }
			end
		end
	end
end

-- position actuelle du pied k (en l'air : arc au-dessus de la surface)
function G.pied(m, k: number, t: number, haut: Vector3): Vector3?
	local a = m.air[k]
	if a then
		local u = lisse((t - a.t0) / a.duree)
		return a.debut:Lerp(a.fin, u) + haut * (a.hauteur * math.sin(math.pi * u))
	end
	return m.pieds[k]
end

-- chemin d'un bras posé : il se cambre au-dessus de la surface jusqu'au pied, puis s'étale au-delà
-- nF (facultatif) = normale de la surface sous le pied, quand ce n'est pas celle du corps (pied resté au sol pendant
-- qu'elle monte le mur, par exemple) : le bout du bras s'étale alors le long de cette surface-là
function G.cheminPied(B: Vector3, F: Vector3, centre: Vector3, haut: Vector3, nF: Vector3?): { Vector3 }
	local nS = nF or haut
	local dehors = F - centre; dehors = dehors - nS * dehors:Dot(nS)
	dehors = dehors.Magnitude > 1e-3 and dehors.Unit or Vector3.new(1, 0, 0)
	local Fp = F + nS * 0.2
	local pts = { B }
	bezier(B, B + (Fp - B) * 0.35 + haut * 0.5, Fp - dehors * 1.0 + nS * 0.25, Fp, 10, pts)
	table.insert(pts, Fp + dehors * 1.5); table.insert(pts, Fp + dehors * 4)
	return pts
end

-- chemin d'un bras en course : ramené derrière elle, ondulation commune à tous les bras
function G.cheminTrainee(B: Vector3, centre: Vector3, avant: Vector3, haut: Vector3, t: number): { Vector3 }
	local cote = haut:Cross(avant).Unit
	local rel = B - centre
	local lat = rel:Dot(cote)
	local E = centre - avant * 5.6 + cote * lat * 2.0 + haut * 0.25
	local dehors = rel - haut * rel:Dot(haut)
	dehors = dehors.Magnitude > 1e-3 and dehors.Unit or -avant
	local brut = {}
	bezier(B, B + dehors * 1.0 + haut * 0.3, E + avant * 3.0, E, 14, brut)
	local pts = { B }
	for i, p in ipairs(brut) do
		local u = i / #brut
		table.insert(pts, p + cote * (0.35 * u * math.sin(t * 9 - u * 5)))
	end
	table.insert(pts, E - avant * 3)
	return pts
end

-- ================================================================ attaques au contact
G.FOUET = {
	frappe = 0.18,        -- s : la base passe de l'armé au bout de sa course (le reste du bras suit en retard)
	retard = 0.018,       -- s de retard de chaque os sur le précédent : la boucle se déroule et le bout claque en dernier
	suite = 0.55,         -- s : le bras continue, retombe dans l'eau et se reprend
	arme = 2.0,           -- rad : bras levé en arrière (0 = vers la cible, à l'horizontale)
	courbure = 0.24,      -- rad par os : le bras s'enroule vers la pointe pendant l'armé
	depasse = 0.3,        -- rad : la base passe sous la cible
	portee_bras = 5.5,    -- au-delà, elle bondit vers sa cible
	contact = 0.28,       -- s après le signe : le bout du bras arrive sur la cible (pour les dégâts et l'éclaboussure)
}
G.BALAYAGE = { tour = 0.35, enfoncement = 0.3 }

-- angle de la base du bras dans le plan du coup, à l'instant x (x < 0 : avant le geste)
local function angleFouet(x: number, signe: number, aRepos: number, aCible: number): number
	local F = G.FOUET
	if x <= 0 then return aRepos end
	if x < signe then return aRepos + (F.arme - aRepos) * lisse(x / signe) end
	local fin = aCible - F.depasse
	local u = (x - signe) / F.frappe
	if u < 1 then return F.arme + (fin - F.arme) * (u ^ 2.2) end           -- accélère jusqu'au bout : coup de fouet
	local tau = x - signe - F.frappe
	return fin - 0.25 * lisse(tau / 0.35) - 0.2 * math.sin(tau * 10) * math.exp(-tau * 7)   -- retombe et rebondit
end

--[[ fouet : articulations du bras (B = départ du bras, T = cible, cote = côté du bras) et poids global du geste.
Le coup est un arc en biais (de côté et vers le bas), dans un plan qui contient la direction de la cible. Chaque os suit
la base avec un retard croissant : pendant la frappe le bras forme une boucle qui se déroule jusqu'à la pointe. ]]
function G.fouetBras(e: number, signe: number, B: Vector3, T: Vector3, centre: Vector3, haut: Vector3, L: { number }): ({ Vector3 }, number)
	local F = G.FOUET
	local vers = T - B; vers = vers - haut * vers:Dot(haut)
	local avant = vers.Magnitude > 1e-3 and vers.Unit or Vector3.new(1, 0, 0)
	local lat = B - centre; lat = lat - haut * lat:Dot(haut) - avant * lat:Dot(avant)
	local cote = lat.Magnitude > 1e-3 and lat.Unit or haut:Cross(avant).Unit
	local plan = (haut * 0.9 + cote * 0.45).Unit
	local v = T - B
	local aCible = math.atan2(v:Dot(plan), v:Dot(avant))
	local frappe = lisse((e - signe) / F.frappe)
	local courbe = F.courbure * lisse(e / signe) * (1 - frappe) - 0.05 * frappe * (1 - lisse((e - signe - F.frappe) / 0.3)) + 0.04 * lisse((e - signe - F.frappe) / 0.3)
	local J = {}
	local cur = B
	for j = 1, #L do
		local x = e - F.retard * (j - 1)
		local a = angleFouet(x, signe, 0.15, aCible) + courbe * (j - 1)
		a += 0.06 * math.sin(9 * e - 0.9 * j) * (1 - frappe)                -- le bras ondule pendant l'armé
		cur = cur + (avant * math.cos(a) + plan * math.sin(a)) * L[j]
		J[j] = cur
	end
	local global = lisse(e / 0.15) * (1 - lisse((e - signe - F.frappe - 0.25) / 0.3))
	return J, global
end

-- fouet : corps qui recule et pivote pendant l'armé, puis bondit vers la cible et pivote dans l'autre sens à la frappe
-- (cote = +1 si le bras qui frappe est à gauche, -1 à droite)
function G.fouetCorps(e: number, signe: number, distance: number, cote: number): CFrame
	local F = G.FOUET
	local arme = lisse(e / signe)
	local coup = lisse((e - signe + 0.04) / F.frappe) * (1 - lisse((e - signe - F.frappe - 0.1) / 0.4))
	local fin = 1 - lisse((e - signe - F.frappe - 0.1) / 0.4)
	local bond = math.clamp(distance - F.portee_bras, 0, 3.5)
	local pivot = cote * (0.16 * arme * (1 - coup) - 0.2 * coup) * fin
	-- elle se dresse sur ses bras arrière pour frapper de haut, puis se rabat vers l'avant
	return CFrame.new(bond * coup, 0.9 * arme * fin, 0) * CFrame.Angles(0, pivot, 0)
		* autourPivot(G.CABRE_PIVOT, (0.22 * arme * (1 - coup) - 0.08 * coup) * fin)
end

-- balayage : elle s'aplatit, puis fait un tour complet ; renvoie le repère du corps, la vitesse de rotation et le poids des bras tendus
function G.balayage(e: number, signe: number): (CFrame, number, number)
	local B = G.BALAYAGE
	if e < signe then
		local a = lisse(e / signe)
		return CFrame.new(0, -B.enfoncement * a, 0), 0, 0
	end
	local u = math.clamp((e - signe) / B.tour, 0, 1)
	local ang = 2 * math.pi * (1 - (1 - u) ^ 3)
	local omega = (u < 1) and (2 * math.pi * 3 * (1 - u) ^ 2 / B.tour) or 0
	local poids = lisse((e - signe + 0.08) / 0.08) * (1 - lisse((e - signe - B.tour) / 0.4))
	return CFrame.new(0, -B.enfoncement * (1 - u), 0) * CFrame.Angles(0, ang, 0), omega, poids
end
-- bras tendu à ras de l'eau, recourbé vers l'arrière de la rotation (sens trigonométrique vu du dessus)
function G.cheminBalayage(B: Vector3, centre: Vector3, haut: Vector3, omega: number): { Vector3 }
	local rel = B - centre; rel = rel - haut * rel:Dot(haut)
	local r0 = rel.Magnitude
	local d = r0 > 1e-3 and rel.Unit or Vector3.new(1, 0, 0)
	local cote = haut:Cross(d)
	local kappa = 0.004 * omega
	local pts = { B }
	for i = 1, 20 do
		local s = i * 0.35
		local a = -kappa * s
		table.insert(pts, centre + (d * math.cos(a) + cote * math.sin(a)) * (r0 + s) + haut * (0.6 * math.min(1, s / 1.5)))
	end
	return pts
end

-- ================================================================ chute dévorante, plaquage
--[[ cage : les huit bras descendent le long du torse de la victime en se croisant (N = base de la tête, U = axe du corps).
Chaque bras part de son côté et tourne autour du corps en descendant (sens alterné d'un bras à l'autre). ]]
function G.cheminCage(B: Vector3, N: Vector3, U: Vector3, sens: number): { Vector3 }
	local rel = B - N; rel = rel - U * rel:Dot(U)
	local d = rel.Magnitude > 1e-3 and rel.Unit or U:Cross(Vector3.new(1, 0, 0)).Unit
	local l = U:Cross(d).Unit
	local pts = { B }
	for i = 1, 24 do
		local s = i * 0.25
		local a = sens * 0.35 * s
		local r = 1.05 + 0.25 * math.min(1, s)
		table.insert(pts, N + (d * math.cos(a) + l * math.sin(a)) * r - U * (0.15 + s * 0.75))
	end
	return pts
end

-- bond (plaquage) : position et bascule du corps le long d'une parabole ; u = avancement 0..1
function G.bond(depart: Vector3, arrivee: Vector3, hauteur: number, u: number): (Vector3, number)
	u = math.clamp(u, 0, 1)
	local p = depart:Lerp(arrivee, u) + Vector3.new(0, 4 * hauteur * u * (1 - u), 0)
	return p, 0.4 * (1 - 2 * u)                          -- avant relevé au départ, plongeant à l'arrivée
end

--[[ plaquage : à l'impact elle se colle contre la poitrine du joueur, le dessous (bras, ventouses) contre lui, la tête vers
la sienne ; quand il tombe à la renverse, elle reste collée et finit couchée sur lui. v = repère du HumanoidRootPart. ]]
G.PLAQUE_OFF = Vector3.new(0, 0.2, -0.6)                    -- dans le repère du joueur : contre la poitrine
function G.plaqueRepere(v: CFrame): CFrame
	return CFrame.fromMatrix(v * G.PLAQUE_OFF, v.UpVector, v.LookVector)   -- X (avant du modèle) = vers sa tête, Y = hors de sa poitrine
end
-- repère affiché pendant le bond : en vol l'avant se relève peu à peu pour présenter le dessous, si bien qu'elle arrive
-- exactement dans la pose collée contre un joueur debout qui lui fait face
local ROT_MODELE = CFrame.Angles(0, math.pi / 2, 0)
function G.bondRepere(depart: Vector3, arrivee: Vector3, hauteur: number, u: number): CFrame
	local pos, bascule = G.bond(depart, arrivee, hauteur, u)
	local dir = Vector3.new(arrivee.X - depart.X, 0, arrivee.Z - depart.Z)
	dir = dir.Magnitude > 1e-3 and dir.Unit or Vector3.new(0, 0, -1)
	local vol = CFrame.lookAt(pos, pos + dir, Vector3.yAxis) * ROT_MODELE * CFrame.Angles(0, 0, bascule)
	local colle = CFrame.fromMatrix(pos, Vector3.yAxis, -dir)
	return vol:Lerp(colle, lisse((u - 0.35) / 0.65))
end

-- plaquage, ramassé avant le bond : le corps se tasse et recule un peu
function G.ramasse(e: number, signe: number): CFrame
	local a = lisse(e / signe)
	return CFrame.new(-0.4 * a, -0.3 * a, 0) * autourPivot(G.CABRE_PIVOT, 0.1 * a)
end

-- enlèvement : suspendue à la grille (repère retourné du plafond : +Y du modèle = vers le bas). Pendant le signe, prog = 0..1 ;
-- ensuite tt = temps depuis la saisie : elle remonte à mesure qu'elle hisse la victime, puis rentre dans la gaine.
function G.suspendre(prog: number, tt: number?, E: any): CFrame
	local h, rentre = lisse(prog), 0
	if tt then
		h = 1 - 0.7 * lisse((tt - E.trainee) / E.levee)
		rentre = lisse((tt - E.trainee - E.levee) / E.avalee)
		h *= (1 - rentre)
	end
	return CFrame.new(0, 2.5 * h - 2.5 * rentre, 0) * autourPivot(G.PIVOT_ARRIERE, 0.9 * h)
end

-- ================================================================ chute dévorante : bras en coupe
--[[ coupe : les bras se ramassent autour d'un axe (vers la tête visée), s'évasent puis se recourbent vers l'intérieur au bout,
comme une main prête à se refermer. ouverture = rayon de la coupe ; t sert au frémissement. ]]
function G.cheminCoupe(B: Vector3, centre: Vector3, axe: Vector3, ouverture: number, t: number, k: number): { Vector3 }
	local rel = B - centre; rel = rel - axe * rel:Dot(axe)
	local r0 = rel.Magnitude
	local d = r0 > 1e-3 and rel.Unit or axe:Cross(Vector3.new(1, 0, 0)).Unit
	local l = axe:Cross(d)
	local pts = { B }
	for i = 1, 24 do
		local s = i * 0.3
		local r = r0 + (ouverture - r0) * math.sin(math.min(1, s / 3.5) * math.pi / 2)
		r -= 0.9 * math.max(0, (s - 4.5) / 2.7) ^ 1.5                          -- le bout se recourbe vers l'intérieur
		r += 0.04 * math.sin(t * 22 + k * 1.7 + s)                              -- frémissement
		local a = 0.1 * math.sin(t * 3 + k)                                     -- léger vrillage, différent pour chaque bras
		table.insert(pts, centre + (d * math.cos(a) + l * math.sin(a)) * r + axe * (s * 0.85))
	end
	return pts
end

--[[ chute dévorante, pendant l'attente : bras ramassés à plat contre le plafond, chacun enroulé sur lui-même près du corps
(rien ne pend). serre = 0..1 : les spirales se resserrent juste avant qu'elle se lâche. haut = dessus du corps (vers le sol
quand elle est au plafond) : les bras restent du côté du plafond. ]]
function G.cheminRamasse(B: Vector3, centre: Vector3, haut: Vector3, serre: number, t: number, k: number): { Vector3 }
	local rel = B - centre; rel = rel - haut * rel:Dot(haut)
	local d = rel.Magnitude > 1e-3 and rel.Unit or haut:Cross(Vector3.new(1, 0, 0)).Unit
	local l = haut:Cross(d).Unit * ((k % 2 == 0) and 1 or -1)          -- un bras sur deux s'enroule dans l'autre sens
	local plan = centre - haut * (centre - B):Dot(haut) - haut * 0.12
	local R = (2.3 - 0.35 * serre) * (1 + 0.025 * math.sin(t * 7 + k))     -- frémissement de tension
	local pts = { B }
	local r0 = rel.Magnitude
	for i = 1, 6 do                                                     -- droit vers l'extérieur, plaqué
		local r = r0 + (R - r0) * (i / 6)
		table.insert(pts, plan + d * r)
	end
	local fin = plan + d * R
	local rho0 = 0.75 - 0.15 * serre
	local C = fin + l * rho0
	for i = 1, 24 do                                                    -- puis enroulé en spirale vers l'intérieur
		local phi = i / 24 * 1.7 * math.pi
		local rho = rho0 * (1 - 0.55 * i / 24)
		table.insert(pts, C + (-l * math.cos(phi) + d * math.sin(phi)) * rho)
	end
	return pts
end

--[[ poids d'orientation pour l'os j d'une chaîne quand on veut que tout le bras ait fait la fraction p du chemin :
chaque os se tourne d'une part de ce qui reste après ses parents, donc des poids égaux s'additionnent vers la pointe
(un bras « claque » en quelques images). Ce poids-là donne une progression régulière. ]]
function G.poidsChaine(p: number, j: number): number
	p = math.clamp(p, 0, 1)
	if p >= 1 then return 1 end
	return 1 - (1 - p) ^ (1 / j)
end

-- longueur d'un chemin, et le même chemin coupé à une longueur donnée
function G.longueur(pts: { Vector3 }): number
	local s = 0
	for i = 2, #pts do s += (pts[i] - pts[i - 1]).Magnitude end
	return s
end
function G.tronquer(pts: { Vector3 }, l: number): { Vector3 }
	local out = { pts[1] }
	local s = 0
	for i = 2, #pts do
		local seg = (pts[i] - pts[i - 1]).Magnitude
		if s + seg >= l then
			table.insert(out, pts[i - 1]:Lerp(pts[i], (l - s) / math.max(seg, 1e-6)))
			return out
		end
		s += seg; table.insert(out, pts[i])
	end
	return out
end
G.ETIRE_MAX = 4.5                                                       -- le haut d'un bras peut s'allonger jusqu'à 4,5 fois sa longueur

-- ================================================================ plaquage : un bras planté sur un membre
-- il s'enroule autour du membre (P, axe) puis s'enfonce vers le sol pour le clouer
function G.cheminPlante(B: Vector3, P: Vector3, axe: Vector3, centre: Vector3, haut: Vector3, sens: number): { Vector3 }
	local f = centre - P; f = f - axe * f:Dot(axe); f = f.Magnitude > 1e-3 and f.Unit or haut
	local pts = G.cheminEnroule(B, P, axe, f, 0.42, 0, sens, 1.1)
	local fin = pts[#pts]
	table.insert(pts, fin - haut * 1.2); table.insert(pts, fin - haut * 2.5)
	return pts
end
-- attribue les huit bras aux huit points (sans croisement) : bras et points triés par angle autour d'elle, décalage circulaire optimal
function G.attribuer(bases: { [number]: Vector3 }, points: { Vector3 }, centre: Vector3, haut: Vector3, avant: Vector3): { [number]: number }
	local cote = haut:Cross(avant)
	local function angle(v: Vector3): number
		local r = v - centre
		return math.atan2(r:Dot(cote), r:Dot(avant))
	end
	local bras = {}
	for k, b in pairs(bases) do table.insert(bras, { k = k, a = angle(b) }) end
	table.sort(bras, function(x, y) return x.a < y.a end)
	local pts = {}
	for i, p in ipairs(points) do table.insert(pts, { i = i, a = angle(p) }) end
	table.sort(pts, function(x, y) return x.a < y.a end)
	local n = math.min(#bras, #pts)
	local best, bd = 0, math.huge
	for dec = 0, n - 1 do
		local tot = 0
		for i = 1, n do tot += (bases[bras[i].k] - points[pts[((i - 1 + dec) % n) + 1].i]).Magnitude end
		if tot < bd then best, bd = dec, tot end
	end
	local out = {}
	for i = 1, n do out[bras[i].k] = pts[((i - 1 + best) % n) + 1].i end
	return out
end

-- ================================================================ enlèvement : bras qui sortent d'une grille du plafond
-- passage du bras k dans l'ouverture (O = centre de la grille, juste en dessous) ; dir = direction du bras autour de l'axe vertical
function G.passageGrille(O: Vector3, dir: Vector3): Vector3
	return O + dir * 0.9 - Vector3.new(0, 0.3, 0)
end
-- du corps (caché dans la gaine) jusqu'au passage, puis la suite du chemin
function G.parLaGrille(B: Vector3, passage: Vector3, suite: { Vector3 }): { Vector3 }
	local pts = { B }
	bezier(B, B + Vector3.new(0, -0.6, 0), passage + Vector3.new(0, 0.8, 0), passage, 6, pts)
	for i = 2, #suite do table.insert(pts, suite[i]) end
	return pts
end
-- bras pendant de la grille qui se balance, attiré vers la cible
function G.cheminPendant(passage: Vector3, vers: Vector3, t: number, k: number): { Vector3 }
	local h = Vector3.new(vers.X - passage.X, 0, vers.Z - passage.Z)
	h = h.Magnitude > 1e-3 and h.Unit or Vector3.new(1, 0, 0)
	local lat = Vector3.new(-h.Z, 0, h.X)
	local pts = { passage }
	for i = 1, 20 do
		local s = i * 0.35
		table.insert(pts, passage + h * (0.35 * s) - Vector3.new(0, s, 0) + lat * (0.25 * math.sin(2.5 * t - 0.8 * s + k)))
	end
	return pts
end
-- hissage par à-coups : trois tractions rapides séparées de courtes pauses ; u = 0..1 -> avancement
function G.aCoups(u: number, nb: number?): number
	local n: number = nb or 3
	u = math.clamp(u, 0, 1)
	local i = math.min(n - 1, math.floor(u * n))
	local f = u * n - i
	return (i + lisse(math.min(1, f / 0.45))) / n
end

-- ================================================================ passage d'une grille (plafond <-> gaine)
local UPV = Vector3.yAxis
local function dirH(v: Vector3, defaut: Vector3): Vector3
	local h = Vector3.new(v.X, 0, v.Z)
	return h.Magnitude > 0.3 and h.Unit or defaut
end
local function angleH(v: Vector3): number return math.atan2(v.Z, v.X) end
local function versH(a: number): Vector3 return Vector3.new(math.cos(a), 0, math.sin(a)) end
local function ecartAngle(a: number, b: number): number return (b - a + math.pi) % (2 * math.pi) - math.pi end

--[[ Montée (plafond -> gaine) : sous la grille, elle se tourne (tête à l'opposé de la gaine où elle va) pendant que ses bras
passent entre les barreaux et s'agrippent au fond de la gaine ; puis elle s'y hisse par à-coups en basculant (tête d'abord,
le ventre contre la paroi), le manteau passe en dernier et se rabat derrière elle. Descente : l'inverse, tête la première.
u = 0..1 ; de = position de la racine au départ, vers = un point de l'autre côté (seule sa hauteur compte, et l'axe de la gaine) ; passage = centre de la grille ; avant0 = direction
du corps au départ. Renvoie le repère affiché (X = avant du modèle, Y = dessus) et deux réglages d'écrasement du corps :
serre (bras ramenés contre le corps quand il passe les barreaux) et etire (manteau allongé quand il passe). ]]
G.TRAV = { a1 = 0.28, a2 = 0.72 }
function G.traversee(u: number, de: Vector3, vers: Vector3, passage: Vector3, avant0: Vector3, montee: boolean): (CFrame, number, number)
	local T = G.TRAV
	u = math.clamp(u, 0, 1)
	local a0 = dirH(avant0, Vector3.new(1, 0, 0))
	local serre = math.sin(math.pi * math.clamp((u - T.a1) / (0.9 - T.a1), 0, 1))
	local etire = math.sin(math.pi * math.clamp((u - 0.5) / 0.45, 0, 1))
	if montee then
		local axe = dirH(vers - passage, a0)                   -- axe de la gaine ; le sens le plus proche du sien (jamais plus d'un quart de tour)
		local d = axe:Dot(a0) <= 0 and axe or -axe
		local Q1 = Vector3.new(passage.X, de.Y, passage.Z)
		local Q2 = Vector3.new(passage.X, vers.Y, passage.Z)
		if u < T.a1 then
			local s = lisse(u / T.a1)
			local psi = angleH(a0) + ecartAngle(angleH(a0), angleH(-d)) * s
			return CFrame.fromMatrix(de:Lerp(Q1, s), versH(psi), -UPV), 0, 0
		end
		local th, pos
		if u < T.a2 then
			local v = G.aCoups((u - T.a1) / (T.a2 - T.a1), 3)
			pos = Q1:Lerp(Q2, v); th = math.pi / 2 * v
		else
			local w = lisse((u - T.a2) / (1 - T.a2))
			pos = Q2:Lerp(Q2 + d * 1.2, w) + UPV * (0.3 * math.sin(math.pi * w)); th = math.pi / 2 * (1 + w)   -- elle se couche vers l'avant
		end
		return CFrame.fromMatrix(pos, -d * math.cos(th) + UPV * math.sin(th), -d * math.sin(th) - UPV * math.cos(th)), serre, etire
	else
		local axe = dirH(passage - de, a0)
		local d = axe:Dot(a0) >= 0 and axe or -axe
		local Q2 = Vector3.new(passage.X, de.Y, passage.Z)
		local Q1 = Vector3.new(passage.X, vers.Y, passage.Z)
		if u < T.a1 then
			local s = lisse(u / T.a1)
			local psi = angleH(a0) + ecartAngle(angleH(a0), angleH(d)) * s
			return CFrame.fromMatrix(de:Lerp(Q2, s), versH(psi), UPV), 0, 0
		end
		local th, pos
		if u < T.a2 then
			local v = G.aCoups((u - T.a1) / (T.a2 - T.a1), 3)
			pos = Q2:Lerp(Q1, v); th = math.pi / 2 * v
		else
			local w = lisse((u - T.a2) / (1 - T.a2))
			pos = Q1:Lerp(Q1 - d * 1.2, w) - UPV * (0.3 * math.sin(math.pi * w)); th = math.pi / 2 * (1 + w)
		end
		return CFrame.fromMatrix(pos, d * math.cos(th) - UPV * math.sin(th), d * math.sin(th) + UPV * math.cos(th)), serre, etire
	end
end

--[[ bras pendant le passage : chacun passe entre deux barreaux (G) puis s'agrippe de l'autre côté (A, sur la surface
d'arrivée de normale n), et s'y étale. Quand la base du bras est déjà passée, le détour par les barreaux disparaît. ]]
function G.cheminTraversee(B: Vector3, Gk: Vector3, A: Vector3, n: Vector3, passage: Vector3, dehors: Vector3): { Vector3 }
	local h = (B - passage):Dot(n)
	local V = Gk:Lerp(B, lisse(h / 0.8))
	local pts = { B }
	if (V - B).Magnitude > 0.05 then bezier(B, B + (V - B) * 0.4, V - n * 0.7, V, 6, pts) end
	bezier(V, V + n * 0.7, A + n * 0.8, A, 8, pts)
	table.insert(pts, A + dehors * 2); table.insert(pts, A + dehors * 4.5)
	return pts
end
G.FENTES = { -1.55, -0.93, -0.31, 0.31, 0.93, 1.55 }      -- espaces entre les barreaux d'une grille (studs, depuis le centre)
--[[ où chaque bras s'agrippe de l'autre côté (A[k], direction d'étalement r[k]) et entre quels barreaux il passe (Gk[k]).
barre / fente = axes des barreaux et de leurs intervalles. Ces points servent aussi de pieds quand elle repart en marchant. ]]
function G.ancresTraversee(de: Vector3, vers: Vector3, passage: Vector3, avant0: Vector3, montee: boolean, barre: Vector3, fente: Vector3)
	local n = montee and UPV or -UPV
	local fin = G.traversee(1, de, vers, passage, avant0, montee)
	local base = Vector3.new(passage.X, vers.Y, passage.Z) + n * 0.05
	local d = dirH(montee and (vers - passage) or (de - passage), Vector3.new(fin.RightVector.X, 0, fin.RightVector.Z))   -- le long de la gaine
	if d.Magnitude < 1e-3 then d = Vector3.xAxis end
	local lat = Vector3.new(-d.Z, 0, d.X)
	local A, R, Gs = {}, {}, {}
	for k = 0, 7 do
		local a = k * math.pi / 4 + math.pi / 8
		local r = fin:VectorToWorldSpace(Vector3.new(math.cos(a), 0, -math.sin(a)))
		r = Vector3.new(r.X, 0, r.Z); r = r.Magnitude > 1e-3 and r.Unit or d
		A[k] = base + d * (r:Dot(d) * 2.6) + lat * (r:Dot(lat) * 1.8)
		R[k] = r
		local fx, best = r:Dot(fente) * 1.7, G.FENTES[1]
		for _, f in ipairs(G.FENTES) do if math.abs(f - fx) < math.abs(best - fx) then best = f end end
		Gs[k] = passage + fente * best + barre * math.clamp(r:Dot(barre) * 1.7, -1.8, 1.8)
	end
	return A, R, Gs, n
end

-- ================================================================ escalade d'un mur (sol -> mur -> plafond)
--[[ La racine roule autour de l'arête du bas (rayon R), monte le long du mur, puis roule autour de l'arête du haut. Les arêtes
se passent plus lentement (arete s chacune, départ et arrivée arrêtés) ; sur le mur, vitesse constante V, raccordée sans à-coup.
E0 = pied du mur au sol, n = normale du mur (vers la salle), yH = hauteur du plafond. ]]
G.ESCALADE = { rayon = 1.3, arete = 0.45 }
function G.escaladeDuree(h: number, V: number): number
	local R = G.ESCALADE.rayon
	return 2 * G.ESCALADE.arete + math.max(0, h - 2 * R) / V
end
function G.escalade(x: number, E0: Vector3, n: Vector3, yH: number, V: number): CFrame
	local R, Da = G.ESCALADE.rayon, G.ESCALADE.arete
	local h = yH - E0.Y
	local Lm = math.max(0, h - 2 * R)
	local A1 = R * math.pi / 2
	local Dm = Lm / V
	x = math.clamp(x, 0, 2 * Da + Dm)
	local s
	if x < Da then                                          -- arête du bas : part arrêtée, finit à la vitesse V (Hermite)
		local u = x / Da
		s = (3 * u * u - 2 * u * u * u) * A1 + (u * u * u - u * u) * V * Da
	elseif x < Da + Dm then s = A1 + V * (x - Da)
	else                                                    -- arête du haut : part à la vitesse V, finit arrêtée
		local u = (x - Da - Dm) / Da
		s = A1 + Lm + (3 * u * u - 2 * u * u * u) * A1 + (u - 2 * u * u + u * u * u) * V * Da
	end
	if s < A1 then
		local phi = s / R
		return CFrame.fromMatrix(E0 + (n * math.cos(phi) + UPV * math.sin(phi)) * R,
			-n * math.cos(phi) + UPV * math.sin(phi), UPV * math.cos(phi) + n * math.sin(phi))
	elseif s < A1 + Lm then
		return CFrame.fromMatrix(E0 + UPV * (R + (s - A1)), UPV, n)
	end
	local phi = math.min(math.pi / 2, (s - A1 - Lm) / R)
	local E1 = Vector3.new(E0.X, yH, E0.Z)
	return CFrame.fromMatrix(E1 + (-UPV * math.cos(phi) + n * math.sin(phi)) * R,
		UPV * math.cos(phi) + n * math.sin(phi), n * math.cos(phi) - UPV * math.sin(phi))
end
-- surface du coin sol/mur/plafond : où poser un pied (le point le plus proche sur le sol, le mur ou le plafond)
local function coin(p: Vector3, E: Vector3, L: Vector3, dA: Vector3, dB: Vector3): Vector3
	local r = p - E
	local x, y, l = r:Dot(dA), r:Dot(dB), r:Dot(L)
	if y <= x then return E + L * l + dA * math.max(x, 0) end
	return E + L * l + dB * math.max(y, 0)
end
function G.normaleEscalade(p: Vector3, E0: Vector3, n: Vector3, yH: number): Vector3
	if p.Y < E0.Y + 0.05 then return UPV end
	if p.Y > yH - 0.05 then return -UPV end
	return n
end
function G.surfaceEscalade(p: Vector3, E0: Vector3, n: Vector3, yH: number): Vector3
	local L = n:Cross(UPV)
	if p.Y < (E0.Y + yH) / 2 then return coin(p, E0, L, n, UPV) end
	return coin(p, Vector3.new(E0.X, yH, E0.Z), L, -UPV, n)
end

-- ================================================================ passage d'une porte par le haut (plafond -> mur -> sous le linteau -> mur -> plafond)
--[[ Parcours de la racine fait de segments droits et d'arcs, chacun avec le repère du corps à ses deux bouts (X = avant,
Y = dessus) ; le long d'un arc, le repère tourne autour de l'axe latéral. c = milieu de la porte (horizontal), a = axe de la
porte (côté A -> côté B), fA / fB = position des faces du linteau le long de a (fA < 0 < fB), yL = dessous du linteau,
yHA / yHB = plafonds des deux côtés. Coins rentrants (plafond/mur) : arc de rayon R ; arêtes du linteau : arc de rayon o,
passées lentement. Au plafond et au mur, la racine est au ras de la surface, comme ailleurs. ]]
G.PORTE = { o = 0.35, R = 1.3, arete = 0.32, coin = 0.42, approche = 1.2, acc = 0.25 }
function G.porteParcours(c: Vector3, a: Vector3, fA: number, fB: number, yL: number, yHA: number, yHB: number, V: number)
	local P = G.PORTE
	local o, R = P.o, P.R
	local function h(x: number, y: number): Vector3 return Vector3.new(c.X, y, c.Z) + a * x end
	local segs = {}
	local function ligne(p0: Vector3, p1: Vector3, X: Vector3, Y: Vector3)
		local L = (p1 - p0).Magnitude
		if L > 1e-3 then table.insert(segs, { arc = false, p0 = p0, p1 = p1, X0 = X, Y0 = Y, X1 = X, Y1 = Y, d = L / V }) end
	end
	local function arc(C: Vector3, u0: Vector3, u1: Vector3, r: number, X0: Vector3, X1: Vector3, Y0: Vector3, Y1: Vector3, d: number)
		table.insert(segs, { arc = true, C = C, u0 = u0, u1 = u1, r = r, X0 = X0, X1 = X1, Y0 = Y0, Y1 = Y1, d = d })
	end
	local C1 = h(fA, yHA)                                   -- arêtes rentrantes plafond/mur (la racine reste au ras des surfaces)
	local C2 = h(fB, yHB)
	local E2, E3 = h(fA, yL), h(fB, yL)                     -- arêtes du linteau (la racine s'en écarte de o pour les contourner)
	ligne(C1 - a * (R + P.approche), C1 - a * R, a, -UPV)                                              -- au plafond, vers le mur
	arc(C1, -a, -UPV, R, a, -UPV, -UPV, -a, math.max(R * math.pi / 2 / V, P.coin))                    -- coin plafond/mur : tête en bas
	ligne(C1 - UPV * R, E2 - a * o, -UPV, -a)                                                           -- descend le mur
	arc(E2, -a, -UPV, o, -UPV, a, -a, -UPV, P.arete)                                                    -- arête du linteau
	ligne(E2 - UPV * o, E3 - UPV * o, a, -UPV)                                                          -- sous le linteau
	arc(E3, -UPV, a, o, a, UPV, -UPV, a, P.arete)                                                       -- arête de l'autre côté
	ligne(E3 + a * o, C2 - UPV * R, UPV, a)                                                             -- remonte le mur
	arc(C2, -UPV, a, R, UPV, a, a, -UPV, math.max(R * math.pi / 2 / V, P.coin))                       -- coin mur/plafond
	ligne(C2 + a * R, C2 + a * (R + P.approche), a, -UPV)                                              -- au plafond, de l'autre côté
	local D = 0
	for _, sg in ipairs(segs) do D += sg.d end
	return { segs = segs, D = D }
end
function G.porteDuree(pc): number return pc.D + G.PORTE.acc end
-- repère au temps « nominal » tau (0..D) ; avant 0 et après D, le parcours se prolonge en ligne droite
local function cadreNominal(pc, tau: number): CFrame
	local segs = pc.segs
	if tau <= 0 then
		local sg = segs[1]; local dir = (sg.p1 - sg.p0).Unit
		return CFrame.fromMatrix(sg.p0 + dir * (tau * (sg.p1 - sg.p0).Magnitude / sg.d), sg.X0, sg.Y0)
	end
	for i, sg in ipairs(segs) do
		if tau <= sg.d or i == #segs then
			local u = math.clamp(tau / sg.d, 0, 1)
			if i == #segs and tau > sg.d then
				local dir = (sg.p1 - sg.p0).Unit
				return CFrame.fromMatrix(sg.p1 + dir * ((tau - sg.d) * (sg.p1 - sg.p0).Magnitude / sg.d), sg.X1, sg.Y1)
			end
			if not sg.arc then return CFrame.fromMatrix(sg.p0:Lerp(sg.p1, u), sg.X0, sg.Y0) end
			local phi = u * math.pi / 2
			local cs, sn = math.cos(phi), math.sin(phi)
			return CFrame.fromMatrix(sg.C + (sg.u0 * cs + sg.u1 * sn) * sg.r, sg.X0 * cs + sg.X1 * sn, sg.Y0 * cs + sg.Y1 * sn)
		end
		tau -= sg.d
	end
	return CFrame.identity
end
-- temps réel x -> temps nominal (départ et arrivée en douceur)
local function tauPorte(pc, x: number): number
	local ta, D = G.PORTE.acc, pc.D
	local T = D + ta
	x = math.clamp(x, 0, T)
	if x < ta then return x * x / (2 * ta) end
	if x > T - ta then return D - (T - x) ^ 2 / (2 * ta) end
	return x - ta / 2
end
function G.porte(pc, x: number): CFrame return cadreNominal(pc, tauPorte(pc, x)) end
--[[ bras pendant le passage : en faisceau, ils suivent le chemin que le corps vient de parcourir (ils passent les arêtes
après lui, au même endroit). lat = écart latéral de la base du bras, t = temps (ondulation). ]]
function G.cheminPorte(pc, x: number, B: Vector3, lat: number, t: number): { Vector3 }
	local tau = tauPorte(pc, x)
	local pts = { B }
	local long, prec = 0, B
	for i = 1, 40 do
		local cf = cadreNominal(pc, tau - i * 0.03)
		local u = math.min(1, long / 5.5)
		local q = cf.Position + cf.ZVector * (lat * (1 - 0.6 * u)) + cf.UpVector * 0.25 + cf.ZVector * (0.25 * u * math.sin(t * 8 - u * 5))
		long += (q - prec).Magnitude; prec = q
		table.insert(pts, q)
		if long > 7 then break end
	end
	return pts
end

-- ================================================================ états : étourdie, agonie
--[[ bras inerte étalé au sol (étourdie, agonie) : il part droit, ondule un peu, et un spasme (0..1) soulève et recourbe sa
pointe vers le corps. haut = dessus du corps. ]]
function G.cheminInerte(B: Vector3, centre: Vector3, haut: Vector3, k: number, spasme: number): { Vector3 }
	local dir = B - centre; dir = dir - haut * dir:Dot(haut)
	dir = dir.Magnitude > 1e-3 and dir.Unit or haut:Cross(Vector3.new(1, 0, 0)).Unit
	local lat = haut:Cross(dir).Unit
	local plan = B - haut * 0.15
	local pts = { B }
	for i = 1, 14 do
		local s = i * 0.45
		local q = plan + dir * s + lat * (0.35 * math.sin(s * 0.8 + k * 1.3) * math.min(1, s / 2))
		local bout = math.max(0, s - 2.2)
		q += haut * (spasme * bout * 0.55) - dir * (spasme * bout * bout * 0.06)
		table.insert(pts, q)
	end
	return pts
end
-- spasmes : brèves secousses, décalées d'un bras à l'autre ; frequence en secousses par seconde et par bras
function G.spasme(t: number, k: number, frequence: number): number
	local x = (t * frequence + k * 0.37 + (k % 3) * 0.21) % 1
	return math.exp(-((x - 0.5) / 0.07) ^ 2)
end

-- même chemin rééchantillonné en n points régulièrement espacés ; puis mélange de deux chemins point à point (la forme du bras
-- glisse de l'une à l'autre, sans les retournements qu'on aurait en mélangeant les rotations des os)
function G.reechantillonner(pts: { Vector3 }, n: number): { Vector3 }
	local total = G.longueur(pts)
	local out = { pts[1] }
	local i, acc = 2, 0
	for m = 1, n - 1 do
		local cible = total * m / (n - 1)
		while i <= #pts do
			local seg = (pts[i] - pts[i - 1]).Magnitude
			if acc + seg >= cible or i == #pts then
				table.insert(out, pts[i - 1]:Lerp(pts[i], math.clamp((cible - acc) / math.max(seg, 1e-6), 0, 1)))
				break
			end
			acc += seg; i += 1
		end
	end
	return out
end
function G.melangerChemins(a: { Vector3 }, b: { Vector3 }, w: number): { Vector3 }
	if w <= 0 then return a elseif w >= 1 then return b end
	local A, Bm = G.reechantillonner(a, 30), G.reechantillonner(b, 30)
	local out = {}
	for i = 1, 30 do out[i] = A[i]:Lerp(Bm[i], w) end
	return out
end

return G
