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

return G
