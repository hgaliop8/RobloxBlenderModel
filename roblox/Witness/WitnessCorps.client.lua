--[[ THE WITNESS — corps (LocalScript, StarterPlayer > StarterPlayerScripts).
Chaque joueur affiche sa propre copie du modèle et l'anime os par os à partir de la pièce « WitnessRacine » déplacée par le serveur :
ondulation et marche des bras, respiration du manteau, regard qui suit le joueur, gestes d'attaque, lumières et imitations.
Gère aussi les effets reçus du serveur (recul, chute, saisie, encre, coups à la porte, faux pas, faux messages, élimination).
Modèle attendu : ReplicatedStorage > Witness > WitnessModele (import de witness.glb, squelette inclus). ]]

local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")
local UP = Vector3.new(0, 1, 0)
local UserInputService = game:GetService("UserInputService")
local TextChatService = game:GetService("TextChatService")

local joueur = Players.LocalPlayer
local dossier = RS:WaitForChild("Witness")
local C = require(dossier:WaitForChild("WitnessConfig"))
local G = require(dossier:WaitForChild("WitnessGestes"))
local Eau = require(dossier:WaitForChild("WitnessEau"))
local evEffet = dossier:WaitForChild("WitnessEffet")
local evRegard = dossier:WaitForChild("WitnessRegard")
local evDebat = dossier:WaitForChild("WitnessDebat")
local evMessage = dossier:WaitForChild("WitnessMessage")

local racine = workspace:WaitForChild("WitnessRacine")
local source = dossier:WaitForChild("WitnessModele")

-- ================================================================ préparation du modèle
local corps = source:Clone(); corps.Name = "WitnessCorps"
local os_ = {}; local pieces = {}; local lumieres = {}; local verre = {}
for _, d in ipairs(corps:GetDescendants()) do
	if d:IsA("Bone") then os_[d.Name:gsub("%.%d+$", "")] = d end
	if d:IsA("BasePart") then
		d.Anchored = true; d.CanCollide = false; d.CanTouch = false; d.CanQuery = false; d.Massless = true
		local n = d.Name:gsub("%.%d+$", "")
		local kind, rest = n:match("^(%a)_(.+)$")
		if kind == "V" then
			d.Material = Enum.Material.Glass; d.Transparency = 0.78; d.Color = Color3.fromHex(rest); d.CastShadow = false; d.Reflectance = 0.05
			table.insert(verre, d)
		elseif kind == "P" then
			local hex, _r, m, e = rest:match("^(%x%x%x%x%x%x)_(%d+)_(%d+)_(%d+)$")
			d.Color = Color3.fromHex(hex or "C8C8C8")
			if e and tonumber(e) > 0 then
				d.Material = Enum.Material.Neon; d.CastShadow = false
				table.insert(lumieres, { part = d, couleur = d.Color, rouge = hex == "FF5040", pupille = hex == "6CFF8C" })
			elseif m and tonumber(m) >= 50 then d.Material = Enum.Material.Metal
			else d.Material = Enum.Material.SmoothPlastic; d.Transparency = 0.15 end
		end
		table.insert(pieces, d)
	end
end
corps.Parent = workspace
-- pivot du modèle = os « Racine » (origine du fichier : centre de la créature, au niveau des ventouses)
local osRacine = os_["Racine"]
if osRacine then corps.WorldPivot = CFrame.new(osRacine.WorldPosition) end

-- chaînes des bras : os, longueurs, axe de chaque os dans son repère (vers l'os suivant)
local BRAS = {}
for k = 0, 7 do
	local ch = { os = {}, L = {}, axe = {} }
	for j = 1, 8 do ch.os[j] = os_[("Bras%d_%d"):format(k, j)] end
	if #ch.os == 8 then
		for j = 1, 7 do
			local o = ch.os[j + 1].CFrame.Position
			ch.L[j] = o.Magnitude; ch.axe[j] = o.Unit
		end
		ch.L[8] = ch.L[7] * 1.03; ch.axe[8] = ch.axe[7]
		BRAS[k] = ch
	end
end
-- repère monde d'un os, en tenant compte des Transform déjà posés sur ses parents et sur lui
local function mondeOs(b: Bone): CFrame
	local chaine = {}
	local x: Instance? = b
	while x and x:IsA("Bone") do table.insert(chaine, 1, x); x = x.Parent end
	local cf = (x and x:IsA("BasePart")) and (x :: BasePart).CFrame or CFrame.identity
	for _, o in ipairs(chaine) do cf = cf * o.CFrame * o.Transform end
	return cf
end

-- halo et lampe d'imitation
local ancre = Instance.new("Attachment"); ancre.Parent = osRacine or corps.PrimaryPart or pieces[1]
local halo = Instance.new("PointLight"); halo.Color = Color3.fromRGB(86, 224, 208); halo.Range = 10; halo.Brightness = 0.6; halo.Shadows = false; halo.Parent = ancre
local fausseLampe = Instance.new("SpotLight"); fausseLampe.Color = Color3.fromRGB(255, 236, 205); fausseLampe.Angle = 38; fausseLampe.Range = 45
fausseLampe.Brightness = 0; fausseLampe.Face = Enum.NormalId.Right; fausseLampe.Shadows = true; fausseLampe.Parent = ancre
-- brûlure : fumée et vapeur qui s'échappent du corps
local fumee = Instance.new("ParticleEmitter")
fumee.Texture = "rbxasset://textures/particles/smoke_main.dds"; fumee.Rate = 45; fumee.Enabled = false
fumee.Lifetime = NumberRange.new(0.7, 1.4); fumee.Speed = NumberRange.new(2, 5); fumee.SpreadAngle = Vector2.new(60, 60)
fumee.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.8), NumberSequenceKeypoint.new(1, 3.2) })
fumee.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.35), NumberSequenceKeypoint.new(1, 1) })
fumee.Color = ColorSequence.new(Color3.fromRGB(255, 150, 80), Color3.fromRGB(90, 90, 90))
fumee.LightEmission = 0.3; fumee.RotSpeed = NumberRange.new(-60, 60); fumee.Acceleration = Vector3.new(0, 4, 0); fumee.Parent = ancre

-- ================================================================ animation des os
local ROT = CFrame.Angles(0, math.pi / 2, 0)            -- le devant du modèle (+X) suit le LookVector de la racine
local cfAffiche = racine.CFrame * ROT
local precedent = racine.Position; local vitesse = 0; local vitesseV = Vector3.zero
local phases = {}; for k = 0, 7 do phases[k] = k * 0.79 + (k % 3) * 0.4 end
local function ang(pb, x, z) if pb then pb.Transform = CFrame.Angles(x, 0, z) end end
local function lisse(a) a = math.clamp(a, 0, 1); return a * a * (3 - 2 * a) end

local function regarderVers(o, cible)
	if not o then return end
	local monde = o.WorldCFrame
	local dirLocal = monde:VectorToObjectSpace((cible - monde.Position).Unit)
	local y = Vector3.new(0, 1, 0)
	local angle = math.acos(math.clamp(y:Dot(dirLocal), -1, 1))
	local axe = y:Cross(dirLocal)
	if axe.Magnitude < 1e-4 then o.Transform = CFrame.new(); return end
	o.Transform = CFrame.fromAxisAngle(axe.Unit, math.min(angle, 0.7))
end

local chuteEtat = { phase = "", prog = 0, tau = 0, hautY = 1 }

-- plaquage : vrai pendant le vol du bond
local function bondEnVol(): boolean
	local dep, arr = racine:GetAttribute("BondDepart"), racine:GetAttribute("BondArrivee")
	if typeof(dep) ~= "Vector3" or typeof(arr) ~= "Vector3" then return false end
	local x = workspace:GetServerTimeNow() - (racine:GetAttribute("BondT") or 0)
	return x >= 0 and x <= C.COUPS.plaquage.vol
end
local function persoDe(attribut: string): Model?
	local id = racine:GetAttribute(attribut); if not id then return nil end
	local pl = Players:GetPlayerByUserId(id)
	return pl and pl.Character or nil
end

local function plaqueRacine(): BasePart?
	local ch = persoDe("Plaque")
	return ch and ch:FindFirstChild("HumanoidRootPart") :: BasePart? or nil
end

local function saisieTemps() return workspace:GetServerTimeNow() - (racine:GetAttribute("SaisieT") or workspace:GetServerTimeNow()) end
local function enrouler(t: number)
	local victime = Players:GetPlayerByUserId(racine:GetAttribute("Saisie") or 0)
	local ch = victime and victime.Character; if not ch or not osRacine then return end
	local enlevement = racine:GetAttribute("SaisieType") == "enlevement"
	local tete = ch:FindFirstChild("Head") :: BasePart?
	local torse = (ch:FindFirstChild("UpperTorso") or ch:FindFirstChild("Torso")) :: BasePart?
	local N, U, rFin, tours
	if enlevement then
		if not torse then return end
		U = torse.CFrame.UpVector; N = torse.Position; rFin = math.max(torse.Size.X, torse.Size.Z) * 0.55; tours = 1.2
	else
		if not tete then return end
		U = tete.CFrame.UpVector; N = tete.Position - U * (tete.Size.Y * 0.5); rFin = math.max(tete.Size.X, tete.Size.Z) * 0.5 + 0.08; tours = 1.75   -- la gorge : juste sous la tête, au ras de sa largeur
	end
	local tt = saisieTemps()
	-- le bras se resserre peu à peu, avec un serrement rythmé (même rythme que la secousse du serveur)
	local r = rFin + 0.5 * math.exp(-tt * 0.9) - 0.04 * math.max(0, math.sin(tt * 7))
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local f = Vector3.new(centre.X - N.X, 0, centre.Z - N.Z); f = f.Magnitude > 1e-3 and f.Unit or Vector3.new(1, 0, 0)
	local l = U:Cross(f).Unit
	local poids = {}
	-- enlèvement : quatre bras autour du torse (deux hauts, deux bas) ; étranglement : les deux bras avant autour du cou
	local tenants = enlevement and { [0] = 0.1, [7] = 0.3, [1] = -0.7, [6] = -0.5 } or { [0] = 0.1, [7] = 0.3 }
	for k, h0 in pairs(tenants) do
		local chn = BRAS[k]
		if chn then
			local B = (parent * chn.os[1].CFrame).Position
			local sens = ((B - N):Dot(l) >= 0) and 1 or -1
			local pts = G.cheminEnroule(B, N, U, f, r, h0, sens, tours)
			for j = 1, 8 do poids[j] = G.lisse((tt - 0.05 * (j - 1)) / 0.4) end
			G.orienter(chn, parent, G.articulations(B, pts, chn.L), poids)
		end
	end
	-- bras d'appui : en étoile sur la surface où elle se tient (le sol, ou le plafond autour de la grille)
	local surf = racine.CFrame.UpVector                      -- vers le haut au sol, vers le bas au plafond
	local plan = racine.Position
	local w = 0.9 * G.lisse(tt / 0.5)
	for j = 1, 8 do poids[j] = w end
	for k = 1, 6 do
		local chn = BRAS[k]
		if chn and not tenants[k] then
			local B = (parent * chn.os[1].CFrame).Position
			local dir = B - centre; dir = dir - surf * dir:Dot(surf); dir = dir.Magnitude > 1e-3 and dir.Unit or f
			local c0 = centre - surf * (centre - plan):Dot(surf)
			local Fpt = c0 + dir * 4.2
			G.orienter(chn, parent, G.articulations(B, G.cheminSol(B, dir, Fpt, surf), chn.L), poids)
		end
	end
end
-- chute dévorante : ses huit bras descendent en cage autour du torse de la victime
local function cage(t: number)
	local ch = persoDe("Devore"); if not ch or not osRacine or not racine:GetAttribute("DevoreT") then return end
	local tete = ch:FindFirstChild("Head") :: BasePart?; if not tete then return end
	local U = tete.CFrame.UpVector
	local N = tete.Position - U * (tete.Size.Y * 0.5)
	local tt = workspace:GetServerTimeNow() - (racine:GetAttribute("DevoreT") or 0)
	local parent = mondeOs(osRacine)
	local poids = {}
	for j = 1, 8 do poids[j] = lisse((tt - 0.03 * (j - 1)) / 0.25) end
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		G.orienter(chn, parent, G.articulations(B, G.cheminCage(B, N, U, (k % 2 == 0) and 1 or -1), chn.L), poids)
	end
	_ = t
end

-- plaquage : ses huit bras se plantent sur le joueur, deux par membre (poignet et coude, cheville et genou)
local function pointsMembres(ch: Model): { Vector3 }
	local out = {}
	local function ajouter(bout: string, milieu: string, r6: string)
		local b = ch:FindFirstChild(bout) :: BasePart?
		local m = ch:FindFirstChild(milieu) :: BasePart?
		if b and m then table.insert(out, b.Position); table.insert(out, m.Position); return end
		local p6 = ch:FindFirstChild(r6) :: BasePart?
		if p6 then
			local ax = p6.CFrame.UpVector * (p6.Size.Y * 0.35)
			table.insert(out, p6.Position - ax); table.insert(out, p6.Position + ax * 0.3)
		end
	end
	ajouter("LeftHand", "LeftLowerArm", "Left Arm"); ajouter("RightHand", "RightLowerArm", "Right Arm")
	ajouter("LeftFoot", "LeftLowerLeg", "Left Leg"); ajouter("RightFoot", "RightLowerLeg", "Right Leg")
	return out
end
local function axeMembre(ch: Model, P: Vector3): Vector3
	local best, bd = Vector3.new(0, 1, 0), math.huge
	for _, n in ipairs({ "LeftHand", "LeftLowerArm", "RightHand", "RightLowerArm", "LeftFoot", "LeftLowerLeg", "RightFoot", "RightLowerLeg", "Left Arm", "Right Arm", "Left Leg", "Right Leg" }) do
		local pt = ch:FindFirstChild(n) :: BasePart?
		if pt then local d = (pt.Position - P).Magnitude; if d < bd then best, bd = pt.CFrame.UpVector, d end end
	end
	return best
end
-- quel bras va sur quel membre : calculé une fois par bond, dans la pose où elle se colle contre lui (dessous contre sa poitrine),
-- pour que les bras partent déjà vers leur membre pendant le vol et ne se croisent pas
local BASES_MODELE: { [number]: Vector3 } = {}
do
	local piv = corps:GetPivot()
	for k, chn in pairs(BRAS) do BASES_MODELE[k] = piv:PointToObjectSpace(chn.os[1].WorldPosition) end
end
local plaqueCache = { t = -1 :: number, assign = {} :: { [number]: number } }
local function assignationPlaquage(ch: Model, bt: number, dep: Vector3, arr: Vector3): { [number]: number }?
	if plaqueCache.t == bt then return plaqueCache.assign end
	local points = pointsMembres(ch)
	if #points == 0 then return nil end
	local colle = G.bondRepere(dep, arr, C.COUPS.plaquage.hauteur, 1)
	local bases = {}
	for k, b in pairs(BASES_MODELE) do bases[k] = colle * b end
	plaqueCache.t = bt
	plaqueCache.assign = G.attribuer(bases, points, colle.Position, colle.UpVector, colle.RightVector)
	return plaqueCache.assign
end
local function plaquer(t: number)
	local ch = persoDe("Plaque"); if not ch or not osRacine then return end
	local pt0 = racine:GetAttribute("PlaqueT") or 0
	local tt = workspace:GetServerTimeNow() - pt0
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local haut = cfAffiche.UpVector
	local points = pointsMembres(ch)
	if #points == 0 then return end
	local dep, arr = racine:GetAttribute("BondDepart"), racine:GetAttribute("BondArrivee")
	local assign = (typeof(dep) == "Vector3" and typeof(arr) == "Vector3")
		and assignationPlaquage(ch, racine:GetAttribute("BondT") or 0, dep, arr) or nil
	if not assign then
		local bases = {}
		for k, chn in pairs(BRAS) do bases[k] = (parent * chn.os[1].CFrame).Position end
		assign = G.attribuer(bases, points, centre, haut, cfAffiche.RightVector)
	end
	for k, i in pairs(assign :: { [number]: number }) do
		local chn = BRAS[k]
		local P = points[i]
		if chn and P then
			local B = (parent * chn.os[1].CFrame).Position
			local axe = axeMembre(ch, P)
			local l = axe:Cross((centre - P).Magnitude > 1e-3 and (centre - P).Unit or haut)
			local sens = ((B - P):Dot(l) >= 0) and 1 or -1
			local poids = {}
			for j = 1, 8 do poids[j] = lisse((tt - 0.01 * k - 0.015 * (j - 1)) / 0.15) end   -- ils se referment dès le contact
			G.orienter(chn, parent, G.articulations(B, G.cheminPlante(B, P, axe, centre, haut, sens), chn.L), poids)
		end
	end
	_ = t
end

-- bras qui s'allongent : on écarte les os d'un bras (Bone.Position), la peau s'étire entre eux
local POS0: { [number]: { [number]: Vector3 } } = {}
local ETIRE: { [number]: number } = {}
local NPROX = 5                                        -- seuls les cinq premiers os s'étirent : les trois derniers gardent leur
local BASE_L: { [number]: number } = {}                 -- longueur pour pouvoir s'enrouler serré (un os trop long « saute » l'enroulement)
local DIST_L: { [number]: number } = {}
for k, chn in pairs(BRAS) do
	POS0[k] = {}; ETIRE[k] = 1; BASE_L[k] = 0; DIST_L[k] = 0
	for j = 2, 8 do POS0[k][j] = chn.os[j].Position end
	for j = 1, 8 do if j <= NPROX then BASE_L[k] += chn.L[j] else DIST_L[k] += chn.L[j] end end
end
local function etirer(k: number, s: number)
	if math.abs((ETIRE[k] or 1) - s) < 1e-3 then return end
	ETIRE[k] = s
	local chn = BRAS[k]
	for j = 2, NPROX + 1 do chn.os[j].Position = POS0[k][j] * s end
end
local function longueursEtirees(k: number, s: number): { number }
	local chn = BRAS[k]; local L = {}
	for j = 1, 8 do L[j] = chn.L[j] * (j <= NPROX and s or 1) end
	return L
end

-- enlèvement : son corps est caché dans la gaine ; ses bras passent entre les barreaux de la grille.
-- Quatre bras agrippent le rebord du plafond ; les quatre bras avant s'allongent jusqu'à la proie, l'enroulent,
-- puis raccourcissent à mesure qu'ils la hissent.
-- ================================================================ passage de grille, escalade : horaires partagés avec le serveur
local function traverseeInfo()
	local t0 = racine:GetAttribute("TravT"); if not t0 then return nil end
	local de, vers, pas, av = racine:GetAttribute("TravDe"), racine:GetAttribute("TravVers"), racine:GetAttribute("TravPassage"), racine:GetAttribute("TravAvant")
	if typeof(de) ~= "Vector3" or typeof(vers) ~= "Vector3" or typeof(pas) ~= "Vector3" or typeof(av) ~= "Vector3" then return nil end
	local x = workspace:GetServerTimeNow() - t0
	if x < 0 or x > C.GRILLE_PASSAGE then return nil end
	return { u = x / C.GRILLE_PASSAGE, de = de, vers = vers, passage = pas, avant = av, montee = racine:GetAttribute("TravMontee") == true, t0 = t0 }
end
local escDernier: { E0: Vector3, n: Vector3, yH: number, fin: number }? = nil
local function escaladeInfo()
	local t0 = racine:GetAttribute("EscT"); if not t0 then return nil end
	local E0, n, yH = racine:GetAttribute("EscPied"), racine:GetAttribute("EscNormale"), racine:GetAttribute("EscHaut")
	if typeof(E0) ~= "Vector3" or typeof(n) ~= "Vector3" or type(yH) ~= "number" then return nil end
	local D = G.escaladeDuree(yH - E0.Y, C.VITESSE.mur)
	local x = workspace:GetServerTimeNow() - t0
	if x < 0 or x > D then return nil end
	escDernier = { E0 = E0, n = n, yH = yH, fin = t0 + D }
	return { x = x, E0 = E0, n = n, yH = yH }
end
-- passage d'une porte par le haut (parcours recalculé une fois par passage)
local porteCache = { t = nil :: number?, pc = nil :: any }
local function porteInfo()
	local t0 = racine:GetAttribute("PorteT"); if not t0 then return nil end
	local c, a, f, y = racine:GetAttribute("PorteC"), racine:GetAttribute("PorteA"), racine:GetAttribute("PorteF"), racine:GetAttribute("PorteY")
	if typeof(c) ~= "Vector3" or typeof(a) ~= "Vector3" or typeof(f) ~= "Vector3" or typeof(y) ~= "Vector3" then return nil end
	if porteCache.t ~= t0 then porteCache.t = t0; porteCache.pc = G.porteParcours(c, a, f.X, f.Y, y.X, y.Y, y.Z, C.VITESSE.mur) end
	local pc = porteCache.pc
	local x = workspace:GetServerTimeNow() - t0
	if x < 0 or x > G.porteDuree(pc) then return nil end
	return { pc = pc, x = x, D = G.porteDuree(pc) }
end
-- bras pendant le passage d'une porte : en faisceau, ils suivent le chemin du corps
local function porteBras(t: number, info)
	if not osRacine then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local Z = cfAffiche.ZVector
	local p = lisse(info.x / 0.4) * (1 - lisse((info.x - info.D + 0.45) / 0.45))
	local poids = {}
	for j = 1, 8 do poids[j] = G.poidsChaine(p, j) end
	for _, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		G.orienter(chn, parent, G.articulations(B, G.cheminPorte(info.pc, info.x, B, (B - centre):Dot(Z), t), chn.L), poids)
	end
end

-- pieds posés sur le coin sol/mur/plafond pendant l'escalade, et encore une seconde après (les pieds restés au mur)
local function surfaceMarche(): ((Vector3) -> Vector3)?
	local e = escDernier
	if not e or workspace:GetServerTimeNow() > e.fin + 1 then return nil end
	return function(p: Vector3): Vector3 return G.surfaceEscalade(p, e.E0, e.n, e.yH) end
end

-- écrasement du corps entre les barreaux : bases des bras ramenées vers le centre, manteau allongé
local SERRE_OS: { [Bone]: Vector3 } = {}
for k, chn in pairs(BRAS) do SERRE_OS[chn.os[1]] = chn.os[1].Position end
local MANTEAU_OS: { [Bone]: Vector3 } = {}
for _, nm in ipairs({ "Manteau1", "Manteau2" }) do local b = os_[nm]; if b then MANTEAU_OS[b] = b.Position end end
local serreActuel, etireActuel = 0, 0
local function ecraser(serre: number, etire: number)
	if math.abs(serre - serreActuel) > 1e-3 then
		serreActuel = serre
		for b, p0 in pairs(SERRE_OS) do b.Position = Vector3.new(p0.X * (1 - 0.45 * serre), p0.Y, p0.Z * (1 - 0.45 * serre)) end
	end
	if math.abs(etire - etireActuel) > 1e-3 then
		etireActuel = etire
		for b, p0 in pairs(MANTEAU_OS) do b.Position = p0 * (1 + 0.4 * etire) end
	end
end

local marcheEtat = G.nouvelleMarche()
-- bras pendant le passage d'une grille : entre les barreaux, puis agrippés de l'autre côté. La marche continue dessous :
-- le passage prend le dessus bras par bras, et à la fin les pieds repartent des points où les bras se sont agrippés.
local grilleAxes = { t = nil :: number?, barre = Vector3.zAxis, fente = Vector3.xAxis, relais = nil :: number? }
local function traverseeBras(t: number, info)
	if not osRacine then return end
	if grilleAxes.t ~= info.t0 then                                    -- orientation des barreaux de cette grille
		grilleAxes.t = info.t0; grilleAxes.barre = Vector3.zAxis; grilleAxes.fente = Vector3.xAxis
		local best, bd = nil, 6
		for _, g in ipairs(CollectionService:GetTagged("Grille")) do
			if g:IsA("BasePart") and (g.Position - info.passage).Magnitude < bd then best, bd = g, (g.Position - info.passage).Magnitude end
		end
		if best then grilleAxes.barre = (best :: BasePart).CFrame.LookVector; grilleAxes.fente = (best :: BasePart).CFrame.RightVector end
	end
	local A, R, Gs, n = G.ancresTraversee(info.de, info.vers, info.passage, info.avant, info.montee, grilleAxes.barre, grilleAxes.fente)
	local u = info.u
	if u >= 0.75 and grilleAxes.relais ~= info.t0 then               -- relais vers la marche : les pieds sont là où les bras tiennent
		grilleAxes.relais = info.t0
		marcheEtat.pieds = {}; marcheEtat.air = {}
		for k = 0, 7 do marcheEtat.pieds[k] = A[k] end
	end
	local parent = mondeOs(osRacine)
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		local ordre = ({ [0] = 0, [7] = 0, [1] = 1, [6] = 1, [2] = 2, [5] = 2, [3] = 3, [4] = 3 })[k] or 0
		local p = lisse((u - 0.1 - 0.05 * ordre) / 0.3) * (1 - lisse((u - 0.86) / 0.14))
		local poids = {}
		for j = 1, 8 do poids[j] = G.poidsChaine(p, j) end
		G.orienter(chn, parent, G.articulations(B, G.cheminTraversee(B, Gs[k], A[k], n, info.passage, R[k]), chn.L), poids)
	end
	_ = t
end

local grilleCache = { t = nil :: number?, f = nil :: Vector3?, sens = {} :: { [number]: number } }
local function grille(t: number)
	local g = racine:GetAttribute("Grille")
	if typeof(g) ~= "Vector3" or not osRacine then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local O = g - Vector3.new(0, 0.2, 0)
	local e = workspace:GetServerTimeNow() - (racine:GetAttribute("CoupT") or 0)
	local tient = racine:GetAttribute("Saisie") ~= nil
	local tt = tient and (workspace:GetServerTimeNow() - (racine:GetAttribute("SaisieT") or 0)) or 0
	local ch = persoDe("Saisie") or persoDe("Cible")
	local torse = ch and (ch:FindFirstChild("UpperTorso") or ch:FindFirstChild("Torso")) :: BasePart?
	local signe = C.COUPS.enlevement.signe
	-- arrivée des bras, régulière sur 0,7 s
	local p0 = lisse(e / 0.7)
	local nouveaux = false
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		local dir = Vector3.new(B.X - centre.X, 0, B.Z - centre.Z); dir = dir.Magnitude > 1e-3 and dir.Unit or Vector3.new(1, 0, 0)
		local passage = G.passageGrille(O, dir)
		local avantBras = (k == 0 or k == 1 or k == 6 or k == 7)
		local chemin
		local s = 1
		if avantBras and torse then
			-- vers le torse, puis autour : le bras s'allonge le long de ce chemin (jusqu'au contact pendant le signe)
			local U = torse.CFrame.UpVector
			-- quand il passe la grille, les bras glissent le long de son corps et le poussent par les jambes
			local N = torse.Position
			if N.Y > O.Y - 1.3 then N = Vector3.new(N.X, O.Y - 1.3, N.Z) end
			-- direction vers la grille et sens d'enroulement : figés à la saisie (sous la grille ils ne sont plus définis)
			local f, sens
			local fige = tient and grilleCache.t == racine:GetAttribute("SaisieT") and grilleCache.f
			if fige then f = fige; sens = grilleCache.sens[k] or 1
			else
				f = Vector3.new(O.X - N.X, 0, O.Z - N.Z); f = f.Magnitude > 1e-3 and f.Unit or Vector3.new(1, 0, 0)
				sens = ((passage - N):Dot(U:Cross(f).Unit) >= 0) and 1 or -1
				if tient then grilleCache.f = f; grilleCache.sens[k] = sens; nouveaux = true end
			end
			local r = 1.1 + 0.4 * math.exp(-tt * 0.9) - 0.04 * math.max(0, math.sin(tt * 7))
			local h0 = ({ [0] = 0.3, [7] = 0.5, [1] = -0.5, [6] = -0.3 })[k] or 0
			local complet = G.parLaGrille(B, passage, G.cheminEnroule(passage, N, U, f, r, h0, sens, 0.9))
			-- longueur du haut du bras (étiré) : pendant le signe, assez pour que la pointe touche le torse ; une fois saisi,
			-- jusqu'au contact (la pointe, de longueur normale, enroule le torse) ; elle diminue à mesure qu'il est hissé
			local contact = G.longueur(table.move(complet, 1, math.min(#complet, 17), 1, {}))
			local lp
			if tient then lp = math.max(0, contact - DIST_L[k]) + math.min(contact, DIST_L[k]) * lisse(tt / 0.4)
			else lp = BASE_L[k] + math.max(0, contact - DIST_L[k] - BASE_L[k]) * lisse((e - 0.15 - 0.04 * (k % 4)) / (signe - 0.35)) end
			s = math.clamp(lp / BASE_L[k], 1, G.ETIRE_MAX)
			chemin = complet
		elseif avantBras then
			chemin = G.parLaGrille(B, passage, G.cheminPendant(passage, O + dir * 4 - Vector3.new(0, 4, 0), t, k))
		else                                                            -- agrippé au rebord, à plat sous le plafond
			chemin = G.parLaGrille(B, passage, G.cheminSol(passage, dir, Vector3.new(g.X, g.Y - 0.25, g.Z) + dir * 2.8, Vector3.new(0, -1, 0)))
		end
		etirer(k, s)
		local poids = {}
		for j = 1, 8 do poids[j] = G.poidsChaine(p0, j) end
		G.orienter(chn, parent, G.articulations(B, chemin, longueursEtirees(k, s)), poids)
	end
	if nouveaux then grilleCache.t = racine:GetAttribute("SaisieT") end
end

-- chute dévorante, pendant l'attente : bras enroulés à plat contre le plafond ; serre = resserrement juste avant de se lâcher
local function ramasser(t: number, w: number, serre: number)
	if not osRacine or w < 0.001 then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local haut = cfAffiche.UpVector
	local poids = {}
	for j = 1, 8 do poids[j] = w end
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		G.orienter(chn, parent, G.articulations(B, G.cheminRamasse(B, centre, haut, serre, t, k), chn.L), poids)
	end
end
-- chute dévorante : en tombant, ses bras s'ouvrent en ombrelle vers la tête visée
local function coupe(t: number, w: number, ouverture: number)
	if not osRacine or w < 0.001 then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local ch = persoDe("Devore") or persoDe("Cible")
	local tete = ch and ch:FindFirstChild("Head") :: BasePart?
	local axe = tete and (tete.Position - centre) or cfAffiche.UpVector
	axe = axe.Magnitude > 1e-3 and axe.Unit or Vector3.new(0, -1, 0)
	local poids = {}
	for j = 1, 8 do poids[j] = w end
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		G.orienter(chn, parent, G.articulations(B, G.cheminCoupe(B, centre, axe, ouverture, t, k), chn.L), poids)
	end
end

-- états : bras inertes posés au sol, avec des secousses (frequence par bras et par seconde, force 0..1+)
local function inertes(t: number, w: number, frequence: number, force: number)
	if not osRacine or w < 0.001 then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local haut = cfAffiche.UpVector
	local poids = {}
	for j = 1, 8 do poids[j] = G.poidsChaine(w, j) end
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		G.orienter(chn, parent, G.articulations(B, G.cheminInerte(B, centre, haut, k, force * G.spasme(t, k, frequence)), chn.L), poids)
	end
end

-- mort : bras qui se débattent au sol (secousses qui s'éteignent), puis qui s'enroulent sur eux-mêmes (forme mélangée)
local function agonie(t: number, force: number, enroule: number)
	if not osRacine then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local haut = cfAffiche.UpVector
	local poids = { 1, 1, 1, 1, 1, 1, 1, 1 }
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		local a = G.cheminInerte(B, centre, haut, k, force * G.spasme(t, k, 2.4))
		local b = G.cheminRamasse(B, centre, haut, 1, t, k)
		G.orienter(chn, parent, G.articulations(B, G.melangerChemins(a, b, enroule), chn.L), poids)
	end
end

-- ================================================================ marche à pieds posés
local DIRS = {}                       -- direction de chaque bras au repos, dans le repère du modèle
do
	local piv = corps:GetPivot()
	for k, chn in pairs(BRAS) do
		local d = piv:VectorToObjectSpace(chn.os[8].WorldPosition - chn.os[1].WorldPosition)
		d = Vector3.new(d.X, 0, d.Z)
		if d.Magnitude > 1e-3 then DIRS[k] = d.Unit end
	end
end
local poidsLoco = 0
local courseLisse = 0
local P_POSE = { 1, 1, 1, 1, 1, 1, 0.75, 0.5 }       -- les pointes gardent leur enroulement
local P_COURSE = { 1, 1, 1, 1, 1, 1, 0.85, 0.7 }
local function locomotion(t: number, dt: number, actif: boolean)
	poidsLoco += ((actif and 1 or 0) - poidsLoco) * math.min(1, dt * 6)
	if poidsLoco < 0.01 or not osRacine then marcheEtat = G.nouvelleMarche(); return end
	local cf = cfAffiche
	local haut = cf.UpVector
	local vel = vitesseV - haut * vitesseV:Dot(haut)
	-- passage marche <-> course lissé dans le temps (un arrêt net ne fait pas basculer les bras en une image)
	local brute = G.lisse((vel.Magnitude - G.MARCHE.course_debut) / (G.MARCHE.course_plein - G.MARCHE.course_debut))
	courseLisse += (brute - courseLisse) * math.min(1, dt * 7)
	local course = courseLisse
	G.majMarche(marcheEtat, t, cf, DIRS, vel, surfaceMarche(), course > 0.6)
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local avant = vel.Magnitude > 0.5 and vel.Unit or cf.RightVector       -- RightVector du repère affiché = avant du modèle (+X)
	-- marche et course : la forme du bras glisse de l'une à l'autre (mélange des chemins, pas des rotations : les pieds posés
	-- devant et le faisceau derrière sont presque opposés, un mélange de rotations y basculerait d'un coup)
	local w = {}
	for j = 1, 8 do w[j] = poidsLoco * (P_POSE[j] + (P_COURSE[j] - P_POSE[j]) * course) end
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		local chemin
		if course < 0.999 then
			local F = G.pied(marcheEtat, k, t, haut)
			local e = escDernier
			local nF = (F and e and workspace:GetServerTimeNow() <= e.fin + 1) and G.normaleEscalade(F, e.E0, e.n, e.yH) or nil
			if F then chemin = G.cheminPied(B, F, centre, haut, nF) end
		end
		if course > 0.001 then
			local tr = G.cheminTrainee(B, centre, avant, haut, t)
			chemin = chemin and G.melangerChemins(chemin, tr, course) or tr
		end
		if chemin then G.orienter(chn, parent, G.articulations(B, chemin, chn.L), w) end
	end
end

-- ================================================================ attaques au contact
local function cibleAttaque(): Vector3?
	local id = racine:GetAttribute("Cible"); if not id then return nil end
	local pl = Players:GetPlayerByUserId(id); local ch = pl and pl.Character
	local r = ch and ch:FindFirstChild("HumanoidRootPart") :: BasePart?
	return r and r.Position or nil
end
local function horizontal(v: Vector3): Vector3 return Vector3.new(v.X, 0, v.Z) end
local fouetBras = { coupT = -1, k = 0 }
-- décalage du corps affiché pendant une attaque (bond, bascule, tour sur elle-même), dans le repère du modèle
local function decalageGeste(coup: string?, e: number, signe: number): CFrame
	if coup == "fouet" and e < signe + G.FOUET.frappe + G.FOUET.suite then
		local T = cibleAttaque()
		local dist = T and horizontal(T - racine.Position).Magnitude or 0
		return G.fouetCorps(e, signe, dist, (fouetBras.k == 7) and -1 or 1)
	elseif coup == "plaquage" and e < signe then
		return G.ramasse(e, signe)
	elseif coup == "balayage" and e < signe + G.BALAYAGE.tour + 0.4 then
		local corpsCF = G.balayage(e, signe)
		return corpsCF
	end
	return CFrame.identity
end
local P_BALAYAGE = { 1, 1, 1, 1, 1, 1, 0.85, 0.7 }
local function gestesAttaque(coup: string?, e: number, signe: number, coupT: number)
	if not osRacine then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local haut = cfAffiche.UpVector
	if coup == "fouet" and e < signe + G.FOUET.frappe + G.FOUET.suite then
		local T = cibleAttaque() or (centre + cfAffiche.RightVector * 9 + haut * 2)
		if fouetBras.coupT ~= coupT then                     -- le bras avant le plus proche de la cible
			fouetBras.coupT = coupT
			local best, bd = 0, math.huge
			for _, k in ipairs({ 0, 7 }) do
				local chn = BRAS[k]
				if chn then
					local d = ((parent * chn.os[1].CFrame).Position - T).Magnitude
					if d < bd then best, bd = k, d end
				end
			end
			fouetBras.k = best
		end
		local chn = BRAS[fouetBras.k]; if not chn then return end
		local B = (parent * chn.os[1].CFrame).Position
		local J, global = G.fouetBras(e, signe, B, T, centre, haut, chn.L)
		local poids = {}
		for j = 1, 8 do poids[j] = global end
		G.orienter(chn, parent, J, poids)
	elseif coup == "balayage" then
		local _, omega, w = G.balayage(e, signe)
		if w < 0.001 then return end
		local poids = {}
		for j = 1, 8 do poids[j] = P_BALAYAGE[j] * w end
		for _, chn in pairs(BRAS) do
			local B = (parent * chn.os[1].CFrame).Position
			G.orienter(chn, parent, G.articulations(B, G.cheminBalayage(B, centre, haut, omega), chn.L), poids)
		end
	end
end

local function animer(t, dt)
	local mode = racine:GetAttribute("Mode") or "plafond"
	local coup = racine:GetAttribute("Coup"); local coupT = racine:GetAttribute("CoupT") or 0
	local e = workspace:GetServerTimeNow() - coupT; local signe = coup and C.COUPS[coup] and C.COUPS[coup].signe or 0.5
	local saisie = racine:GetAttribute("Saisie") ~= nil
	local etat = racine:GetAttribute("Etat")
	local v = (coup == "descente") and 0 or vitesse                       -- pendant une chute, la vitesse ne fait pas « marcher » les bras
	-- au mur seulement, les bras rament (ailleurs, la marche à pieds posés s'en charge)
	local marche = (mode == "mur" and not escaladeInfo() and not porteInfo()) and math.clamp(v / 10, 0, 1) or 0   -- (escalade : pieds posés)
	local wg = math.min(2 + v * 0.5, 8)
	for k = 0, 7 do
		local ph = phases[k]
		for j = 1, 8 do
			local b = os_[("Bras%d_%d"):format(k, j)]
			-- ondulation de repos : vague qui descend le bras
			local yaw = 0.05 * math.sin(t * 1.1 - j * 0.5 + ph)
			local pitch = 0.025 * math.sin(t * 0.8 + j * 0.6 + ph)
			if j >= 7 then pitch += 0.22 + 0.05 * math.sin(t * 1.4 + ph) end          -- pointes qui s'enroulent
			-- marche : deux groupes de bras qui rament en alternance, les bras levés pendant le retour
			if marche > 0.05 and j <= 4 then
				local g = math.sin(t * wg + (k % 2) * math.pi)
				yaw += marche * 0.28 * g * (1 - (j - 1) / 4)
				pitch += marche * 0.22 * math.max(0, g) * (j >= 2 and 1 or 0)
			end
			if mode == "gaine" then yaw *= 0.4; pitch = pitch * 0.3 - 0.02 end
			if etat == "etourdie" then yaw *= 0.15; pitch = 0.05 * math.sin(t * 9 + j) end
			if etat == "morte" then yaw = 0; pitch = (j >= 5) and 0.3 or 0.05 end
			-- gestes
			if coup == "fouet" then
				-- le bras qui frappe est posé plus bas (gestesAttaque) ; les autres se tendent
				pitch -= 0.05 * lisse(e / signe)
			elseif coup == "balayage" or (coup == "plaquage" and e < signe) then
				-- elle s'aplatit, pointes enroulées ; les bras tendus du tour sont posés plus bas (gestesAttaque)
				local a = (e < signe) and lisse(e / signe) or 1
				pitch += (j <= 2 and -0.1 or (j >= 6 and 0.3 or 0)) * a
			elseif (coup == "saisie" or coup == "enlevement" or saisie) and (k == 0 or k == 7 or k == 1 or k == 6) then
				local a = lisse(e / signe)
				pitch += a * (j == 1 and 0.5 or (j <= 4 and 0.06 or 0.12))        -- bras levés vers la proie, pointes recourbées
				yaw += a * (k <= 1 and 0.2 or -0.2)
			elseif coup == "chute" then
				pitch += 0.12 + 0.03 * math.sin(t * 22 + k)                        -- tension, tremblement
			elseif coup == "descente" and chuteEtat.phase ~= "" then
				local avant = (k == 0 or k == 7 or k == 1 or k == 6)
				local prog, tau = chuteEtat.prog, chuteEtat.tau
				if chuteEtat.phase == "decroche" then
					-- l'avant se décolle et pend, les bras arrière serrent le plafond
					if avant then pitch += prog * (j == 1 and 0.55 or 0.16) + prog * 0.08 * math.sin(t * 9 + j + k)
					elseif j <= 2 then pitch -= 0.3 * prog end
				elseif chuteEtat.phase == "chute" then
					-- les bras traînent vers le haut, puis s'ouvrent vers le sol juste avant l'impact
					local trainee = chuteEtat.hautY * math.min(1, prog * 1.6)
					local pose = lisse((prog - 0.6) / 0.4)
					pitch = pitch * 0.3 + (1 - pose) * (j >= 2 and 0.28 or 0.1) * trainee + pose * (j <= 2 and -0.22 or 0.04)
						+ 0.07 * math.sin(t * 24 + j * 0.8 + k)
				else
					-- impact : les bras claquent à plat puis rebondissent, les pointes se relèvent
					local amorti = math.exp(-7 * tau)
					if j <= 2 then pitch += -0.32 * amorti * math.cos(15 * tau)
					elseif j >= 6 then pitch += 0.45 * math.exp(-5 * tau) end
					yaw *= (1 - 0.6 * amorti)
				end
			elseif coup == "encre" and j <= 3 then
				pitch -= 0.15 * math.sin(math.clamp(e / 0.8, 0, 1) * math.pi)
			end
			ang(b, pitch, yaw)
		end
	end
	-- manteau qui respire, tête, bec
	local respi = math.sin(t * 1.25)
	local contraction = (coup == "encre") and math.sin(math.clamp(e / 0.6, 0, 1) * math.pi) * 0.25 or 0
	if coup == "descente" and chuteEtat.phase == "atterrit" then                 -- le manteau s'écrase à l'impact
		contraction += 0.35 * math.exp(-7 * chuteEtat.tau) * math.cos(12 * chuteEtat.tau)
	end
	-- états : manteau affaissé (étourdie), qui pompe vite (panique), qui se vide et s'aplatit (mort)
	local m1, m2, souffle = 0, 0, 1
	local maintenantE = workspace:GetServerTimeNow()
	if maintenantE < (racine:GetAttribute("Panique") or 0) and etat ~= "morte" then contraction += 0.14 * math.sin(t * 15) end
	if etat == "etourdie" then
		local w = lisse((maintenantE - (racine:GetAttribute("EtatT") or 0)) / 0.6)
		m1 -= 0.3 * w; m2 -= 0.2 * w; souffle = 1 - 0.6 * w
	end
	local mortT = racine:GetAttribute("MortT")
	if etat == "morte" and mortT then
		local xm = maintenantE - mortT
		local w = lisse(xm / 2.2)
		m1 -= 0.45 * w; m2 -= 0.35 * w; souffle = 1 - lisse(xm / 1.2)
		contraction += 0.25 * math.exp(-xm / 0.9) * math.sin(t * 19)               -- derniers spasmes
	end
	ang(os_.Manteau1, (0.05 * respi + contraction) * souffle + m1, 0.02 * math.sin(t * 0.7))
	ang(os_.Manteau2, (0.08 * math.sin(t * 1.25 + 0.5) + contraction) * souffle + m2, 0.04 * math.sin(t * 0.6))
	ang(os_.Tete, 0.03 * math.sin(t * 0.8), 0)
	ang(os_.Bec, 0, 0)
	-- marche : pieds posés au plafond et au sol, faisceau en course (hors gestes d'attaque, chute, saisie)
	local geste = saisie or chuteEtat.phase ~= "" or (coup ~= nil and coup ~= "avorte" and e < signe + 0.8)
		or racine:GetAttribute("Plaque") ~= nil or racine:GetAttribute("Devore") ~= nil or bondEnVol()
		or etat == "morte" or etat == "etourdie"
	local trav = traverseeInfo()                                     -- (la marche continue pendant un passage de grille)
	local surSurface = mode == "plafond" or mode == "sol" or escaladeInfo() ~= nil
	if trav then surSurface = (trav.montee and trav.u < 0.5) or (not trav.montee and trav.u >= 0.75) end   -- au plafond seulement
	locomotion(t, dt, not geste and surSurface)
	-- attaques au contact : bras du fouet, bras tendus du balayage
	gestesAttaque(coup, e, signe, coupT)
	-- plaquage : en vol, bras ramenés en faisceau ; une fois posée, poignets et chevilles tenus ; chute dévorante : cage de bras
	local bt = racine:GetAttribute("BondT")
	local xb = bt and (workspace:GetServerTimeNow() - bt) or -1
	local volB = C.COUPS.plaquage.vol
	if coup == "plaquage" and xb >= 0 and xb < volB + 0.5 and osRacine and typeof(racine:GetAttribute("BondArrivee")) == "Vector3" then
		local dep, arr = racine:GetAttribute("BondDepart"), racine:GetAttribute("BondArrivee")
		local u = xb / volB
		local dir = Vector3.new(arr.X - dep.X, 0, arr.Z - dep.Z); dir = dir.Magnitude > 1e-3 and dir.Unit or cfAffiche.RightVector
		local parent = mondeOs(osRacine)
		local pt0 = racine:GetAttribute("PlaqueT")
		local fin = pt0 and lisse((workspace:GetServerTimeNow() - pt0) / 0.2) or lisse((xb - volB - 0.1) / 0.3)
		local wT = 1 - lisse((u - 0.2) / 0.3)                      -- d'abord ramenés en faisceau...
		local wA = lisse((u - 0.3) / 0.35) * (1 - fin)             -- ...puis lancés chacun vers le membre qu'il va saisir
		local pT, pA = {}, {}
		for j = 1, 8 do pT[j] = wT; pA[j] = wA end
		local centre = parent.Position
		local ch = persoDe("Cible")
		local assign = ch and assignationPlaquage(ch, bt, dep, arr)
		local points = ch and pointsMembres(ch)
		for k, chn in pairs(BRAS) do
			local B = (parent * chn.os[1].CFrame).Position
			if wT > 0.001 then G.orienter(chn, parent, G.articulations(B, G.cheminTrainee(B, centre, dir, UP, t), chn.L), pT) end
			if wA > 0.001 then
				local P = assign and points and points[assign[k]]
				if not P then
					local rad = Vector3.new(B.X - centre.X, 0, B.Z - centre.Z); rad = rad.Magnitude > 1e-3 and rad.Unit or dir
					P = arr + dir + rad * 1.5
				end
				local vise = P :: Vector3
				G.orienter(chn, parent, G.articulations(B, { B, vise, vise + (vise - B).Unit * 0.8 }, chn.L), pA)   -- jusqu'au membre, pas au travers
			end
		end
	end
	if racine:GetAttribute("Plaque") then plaquer(t) end
	if racine:GetAttribute("Grille") then grille(t) end
	if trav then traverseeBras(t, trav) end
	local po = porteInfo()
	if po then porteBras(t, po) end
	-- chute dévorante : pendant l'attente, bras ramassés à plat contre le plafond (rien ne pend) ; en tombant ils s'ouvrent
	-- en ombrelle sous elle, centrée sur la tête ; à l'impact l'ombrelle se referme en cage
	if coup == "chute" and e < signe + 0.5 then
		ramasser(t, lisse(e / 0.5) * (1 - lisse((e - signe - 0.1) / 0.4)), lisse((e - signe + 0.4) / 0.4))
	elseif racine:GetAttribute("Devore") and not racine:GetAttribute("DevoreT") then
		local d = racine:GetAttribute("ChuteDecroche") or C.DECROCHAGE_EMBUSCADE
		local wO = coup == "descente" and lisse((e - d * 0.5) / 0.12) or 0
		ramasser(t, 1 - wO, 1)
		coupe(t, wO, 2.6)
	elseif racine:GetAttribute("Devore") and workspace:GetServerTimeNow() - racine:GetAttribute("DevoreT") < 0.3 then
		coupe(t, 1, 2.6 - 1.25 * lisse((workspace:GetServerTimeNow() - racine:GetAttribute("DevoreT")) / 0.25))   -- l'ombrelle se referme
	end
	if racine:GetAttribute("Devore") then cage(t) end
	-- saisie : les deux bras avant s'enroulent autour du cou (ou du torse pour un enlèvement), les autres prennent appui au sol
	if saisie and not racine:GetAttribute("Grille") then enrouler(t) end
	-- états : étourdie (bras inertes au sol, secousses), mort (convulsions qui s'éteignent, puis bras qui s'enroulent)
	if etat == "etourdie" and mode == "sol" and chuteEtat.phase == "" then
		local xe = maintenantE - (racine:GetAttribute("EtatT") or 0)
		inertes(t, lisse(xe / 0.5) * (1 - lisse((xe - C.ETOURDI_DUREE + 0.7) / 0.7)), 0.55, 0.9)
	end
	if etat == "morte" and mortT then
		local xm = maintenantE - mortT
		agonie(t, 1.4 * math.exp(-xm / 1.1), lisse((xm - 0.9) / 2.0))
	end
	-- brûlure : les bras se tordent dans tous les sens (par-dessus tout le reste)
	local bf = racine:GetAttribute("Brule")
	if bf and etat ~= "morte" then
		local xbr = maintenantE - (bf - C.BRULURE_DUREE)
		local wb = lisse(xbr / 0.1) * (1 - lisse((xbr - C.BRULURE_DUREE + 0.4) / 0.4))
		if xbr >= 0 and wb > 0.01 then
			for k, chn in pairs(BRAS) do
				for j = 2, 8 do
					local a = wb * (0.05 + 0.03 * j)
					chn.os[j].Transform = chn.os[j].Transform * CFrame.Angles(a * math.sin(t * 13 + j * 0.9 + k), 0, 0.8 * a * math.sin(t * 10.5 + j * 0.7 + k * 1.3))
				end
			end
		end
	end
	-- yeux : ils suivent la caméra du joueur s'il est assez proche
	local cam = workspace.CurrentCamera
	if cam and (cam.CFrame.Position - racine.Position).Magnitude < 70 and etat ~= "morte" then
		regarderVers(os_.OeilG, cam.CFrame.Position); regarderVers(os_.OeilD, cam.CFrame.Position)
	end
end

-- ================================================================ lumières, imitations, blessures
local function majLumieres(t)
	local etat = racine:GetAttribute("Etat")
	local maintenant = workspace:GetServerTimeNow()
	local eteinte = maintenant < (racine:GetAttribute("Eteinte") or 0)
	local pv, pvMax = racine:GetAttribute("PV") or 1, racine:GetAttribute("PVMax") or 1
	local sante = math.clamp(pv / pvMax, 0, 1)
	local imitation = racine:GetAttribute("Imitation")
	local coup = racine:GetAttribute("Coup")
	for i, l in ipairs(lumieres) do
		local tr
		local mortT = racine:GetAttribute("MortT")
		if etat == "morte" and mortT then                                             -- elles s'éteignent une à une
			tr = math.clamp((maintenant - mortT - 0.2 - (i % 12) * 0.07) / 0.5, 0, 1)
		elseif etat == "morte" then tr = 0.1 + 0.6 * ((t * 11 + i * 0.3) % 1)               -- en tombant : affolées
		elseif etat == "etourdie" then tr = (math.noise(t * 7, i * 0.37) > 0.12) and 0.85 or 0.3   -- grésillent
		elseif maintenant < (racine:GetAttribute("Panique") or 0) then tr = ((t * 9 + i * 0.13) % 1 < 0.5) and 0 or 0.9
		elseif eteinte then tr = l.pupille and 0.6 or 1
		elseif imitation == "voyants" and not l.pupille then
			-- faux voyants de secours : clignotement dont la période dérive entre 1,6 et 2,6 s (les vrais : 2 s pile)
			local periode = 2.1 + 0.5 * math.sin(t * 0.13 + i)
			tr = ((t / periode) % 1) < 0.5 and 0 or 0.92
		else
			local pulse = 0.5 + 0.5 * math.sin(t * 1.6 + i * 2.1)
			tr = 0.15 + 0.5 * pulse
			if coup == "chute" or coup == "balayage" then tr = 0 end
			if not l.pupille then tr = tr + (1 - sante) * 0.5 end                 -- blessée : les points s'éteignent peu à peu
		end
		l.part.Transparency = math.clamp(tr, 0, 1)
	end
	halo.Enabled = not eteinte and not (etat == "morte" and racine:GetAttribute("MortT") and maintenant - racine:GetAttribute("MortT") > 1.2)
	halo.Brightness = (imitation == "voyants") and 1.2 or 0.5
	halo.Color = (imitation == "voyants") and Color3.fromRGB(255, 70, 50) or Color3.fromRGB(86, 224, 208)
	fausseLampe.Brightness = (imitation == "lampe" and etat ~= "morte") and 3 or 0
	-- mort : le verre devient peu à peu laiteux, puis opaque ; brûlure : il rougit, et fume
	local brule = maintenant < (racine:GetAttribute("Brule") or 0)
	fumee.Enabled = brule and etat ~= "morte"
	local mortT = racine:GetAttribute("MortT")
	local lait = (etat == "morte" and mortT) and lisse((maintenant - mortT - 1.0) / 3.0) or 0
	for _, p in ipairs(verre) do
		if lait >= 1 then p.Material = Enum.Material.SmoothPlastic; p.Transparency = 0.12; p.Color = Color3.fromRGB(230, 232, 228)
		elseif lait > 0 then
			p.Transparency = 0.78 + (0.2 - 0.78) * lait; p.Color = Color3.fromRGB(216, 236, 240):Lerp(Color3.fromRGB(230, 232, 228), lait)
		elseif brule and etat ~= "morte" then p.Color = Color3.fromRGB(255, 150, 90)
		else p.Color = Color3.fromRGB(216, 236, 240) end
	end
end

-- ================================================================ regard du joueur : envoi au serveur, détection « fixer ses lumières »
local fixeDepuis = nil; local dernierEnvoi = 0
local paramsVue = RaycastParams.new(); paramsVue.FilterType = Enum.RaycastFilterType.Exclude
local function regard(t)
	local cam = workspace.CurrentCamera; if not cam then return end
	local look = cam.CFrame.LookVector
	local versElle = racine.Position - cam.CFrame.Position
	local fixe = false
	if versElle.Magnitude < 60 and look:Dot(versElle.Unit) > 0.985 then
		paramsVue.FilterDescendantsInstances = { corps, racine, joueur.Character }
		if not workspace:Raycast(cam.CFrame.Position, versElle, paramsVue) then
			fixeDepuis = fixeDepuis or t
			if t - fixeDepuis > C.FIXEE_DUREE then fixe = true; fixeDepuis = t + 4 end
		end
	else fixeDepuis = nil end
	if t - dernierEnvoi > 0.2 or fixe then dernierEnvoi = t; evRegard:FireServer(look, fixe) end
end

-- décalage du corps selon l'état : recul à la brûlure, affaissement (étourdie), convulsions puis corps qui s'aplatit (mort)
local function decalageEtat(t: number): CFrame
	local maintenant = workspace:GetServerTimeNow()
	local etat = racine:GetAttribute("Etat")
	local cf = CFrame.identity
	local bf = racine:GetAttribute("Brule")
	if bf and etat ~= "morte" then
		local xb = maintenant - (bf - C.BRULURE_DUREE)
		if xb >= 0 and xb < 0.6 then
			local e1 = math.sin(math.pi * xb / 0.6)
			cf = cf * CFrame.new(-0.7 * e1, 0.3 * e1, 0) * CFrame.Angles(0, 0, 0.3 * e1)
		end
		if xb >= 0 and xb < C.BRULURE_DUREE then cf = cf * CFrame.new(0.03 * math.sin(t * 41), 0.02 * math.sin(t * 37), 0) end
	end
	if etat == "etourdie" and chuteEtat.phase == "" and racine:GetAttribute("Mode") == "sol" then
		local xe = maintenant - (racine:GetAttribute("EtatT") or 0)
		local w = lisse(xe / 0.6) * (1 - lisse((xe - C.ETOURDI_DUREE + 0.7) / 0.7))
		cf = cf * CFrame.new(0, -0.35 * w, 0) * CFrame.Angles(0.1 * w * math.sin(t * 0.6), 0, -0.12 * w)
	end
	local mortT = racine:GetAttribute("MortT")
	if etat == "morte" and mortT then
		local xm = maintenant - mortT
		local conv = math.exp(-xm / 1.0)
		local w = lisse(xm / 1.5)
		cf = cf * CFrame.new(0, -0.45 * w + 0.12 * conv * math.abs(math.sin(t * 17)), 0)
			* CFrame.Angles(0.15 * conv * math.sin(t * 13), 0, 0.12 * conv * math.sin(t * 11) - 0.1 * w)
	end
	return cf
end

-- ================================================================ boucle
RunService.RenderStepped:Connect(function(dt)
	local t = os.clock()
	local p = racine.Position
	vitesse = vitesse + (((p - precedent).Magnitude / math.max(dt, 1e-3)) - vitesse) * math.min(1, dt * 6)
	precedent = p
	local avantAff = cfAffiche.Position
	local cible = racine.CFrame * ROT
	local coup = racine:GetAttribute("Coup")
	local depart = racine:GetAttribute("ChuteDepart")
	local e = workspace:GetServerTimeNow() - (racine:GetAttribute("CoupT") or 0)
	local d, tf = racine:GetAttribute("ChuteDecroche") or C.DECROCHAGE, racine:GetAttribute("ChuteTf") or 0.35
	if coup == "descente" and typeof(depart) == "Vector3" and e < d + tf + C.ATTERRISSAGE
		and not (racine:GetAttribute("Devore") and e > d + tf) then
		-- chute : position et orientation calculées ici, à partir du même horaire que le serveur (pas de retard d'affichage)
		local sol = racine:GetAttribute("ChuteSol"); if typeof(sol) ~= "Vector3" then sol = p end
		local modele, tombe, phase, prog, tau = G.chute(e, d, tf, workspace.Gravity, C.ATTERRISSAGE)
		local avant = racine.CFrame.LookVector; avant = Vector3.new(avant.X, 0, avant.Z)
		if avant.Magnitude < 1e-3 then avant = Vector3.new(0, 0, -1) end
		local pos
		if tombe then
			local u = math.clamp((e - d) / tf, 0, 1)
			pos = Vector3.new(depart.X + (sol.X - depart.X) * u, depart.Y - tombe, depart.Z + (sol.Z - depart.Z) * u)
		else pos = sol end
		cfAffiche = CFrame.lookAt(pos, pos + avant.Unit, UP) * ROT * modele
		chuteEtat.phase, chuteEtat.prog, chuteEtat.tau = phase, prog, tau
		chuteEtat.hautY = cfAffiche:VectorToObjectSpace(UP).Y
	elseif traverseeInfo() then
		-- passage d'une grille : repère calculé ici, même horaire que le serveur
		chuteEtat.phase = ""
		local tr = traverseeInfo() :: any
		local cf, serre, etire = G.traversee(tr.u, tr.de, tr.vers, tr.passage, tr.avant, tr.montee)
		cfAffiche = cf; ecraser(serre, etire)
	elseif porteInfo() then
		-- passage d'une porte par le haut : même parcours que le serveur
		chuteEtat.phase = ""
		local po = porteInfo() :: any
		cfAffiche = G.porte(po.pc, po.x)
	elseif escaladeInfo() then
		-- escalade : elle roule autour de l'arête du bas, monte le mur, roule sur le plafond
		chuteEtat.phase = ""
		local es = escaladeInfo() :: any
		cfAffiche = G.escalade(es.x, es.E0, es.n, es.yH, C.VITESSE.mur)
	elseif coup == "plaquage" and bondEnVol() then
		-- bond : parabole calculée ici ; en fin de vol elle se redresse pour arriver le dessous contre sa poitrine
		chuteEtat.phase = ""
		local dep, arr = racine:GetAttribute("BondDepart"), racine:GetAttribute("BondArrivee")
		local P = C.COUPS.plaquage
		local u = (workspace:GetServerTimeNow() - (racine:GetAttribute("BondT") or 0)) / P.vol
		cfAffiche = G.bondRepere(dep, arr, P.hauteur, u)
	elseif racine:GetAttribute("Plaque") and plaqueRacine() then
		-- plaquée sur lui : elle reste collée à sa poitrine pendant qu'il tombe à la renverse, puis couchée sur lui
		chuteEtat.phase = ""
		local hrp = plaqueRacine() :: BasePart
		local colle = G.plaqueRepere(hrp.CFrame)
		local x = workspace:GetServerTimeNow() - (racine:GetAttribute("PlaqueT") or 0)
		local dep, arr = racine:GetAttribute("BondDepart"), racine:GetAttribute("BondArrivee")
		if x < 0.12 and typeof(dep) == "Vector3" and typeof(arr) == "Vector3" then      -- raccord avec la fin du vol
			colle = G.bondRepere(dep, arr, C.COUPS.plaquage.hauteur, 1):Lerp(colle, lisse(x / 0.12))
		end
		cfAffiche = colle
	else
		chuteEtat.phase = ""
		if racine:GetAttribute("Saisie") and racine:GetAttribute("SaisieType") ~= "enlevement" then
			cible = cible * G.cabrer(workspace:GetServerTimeNow() - (racine:GetAttribute("SaisieT") or 0))
		end
		cfAffiche = cfAffiche:Lerp(cible, 1 - math.exp(-14 * dt))
	end
	local coupG = racine:GetAttribute("Coup")
	local signeG = coupG and C.COUPS[coupG] and C.COUPS[coupG].signe or 0.5
	if not traverseeInfo() then ecraser(0, 0) end
	corps:PivotTo(cfAffiche * decalageEtat(t) * decalageGeste(coupG, workspace:GetServerTimeNow() - (racine:GetAttribute("CoupT") or 0), signeG))
	-- vitesse du corps affiché (lissé) : sert à la marche à pieds posés
	vitesseV = vitesseV:Lerp((cfAffiche.Position - avantAff) / math.max(dt, 1e-3), math.min(1, dt * 10))
	if not racine:GetAttribute("Grille") then                 -- hors de la grille, les bras reprennent leur longueur
		for k in pairs(BRAS) do
			local ns = 1 + ((ETIRE[k] or 1) - 1) * math.exp(-dt * 10)
			etirer(k, ns < 1.003 and 1 or ns)
		end
	end
	animer(t, dt)
	majLumieres(t)
	regard(t)
end)

-- ================================================================ effets envoyés par le serveur
local gui = Instance.new("ScreenGui"); gui.Name = "WitnessEcran"; gui.IgnoreGuiInset = true; gui.ResetOnSpawn = false; gui.Parent = joueur:WaitForChild("PlayerGui")
local noir = Instance.new("Frame"); noir.Size = UDim2.fromScale(1, 1); noir.BackgroundColor3 = Color3.new(0, 0, 0); noir.BackgroundTransparency = 1; noir.BorderSizePixel = 0; noir.Parent = gui
local aide = Instance.new("TextLabel"); aide.Size = UDim2.fromScale(1, 0.1); aide.Position = UDim2.fromScale(0, 0.78); aide.BackgroundTransparency = 1
aide.TextColor3 = Color3.new(1, 1, 1); aide.TextStrokeTransparency = 0.3; aide.TextScaled = true; aide.Font = Enum.Font.GothamBold; aide.Text = ""; aide.Parent = gui

local function son(pos, nom, volume)
	local id = C.SONS[nom]; if not id or id == "" then return end
	local a = Instance.new("Attachment"); a.WorldPosition = pos; a.Parent = workspace.Terrain
	local s = Instance.new("Sound"); s.SoundId = id; s.Volume = volume or 1; s.RollOffMaxDistance = 70; s.Parent = a; s:Play()
	task.delay(6, function() a:Destroy() end)
end
local function personnage() return joueur.Character end
local function lumieresJoueur(actif)
	local ch = personnage(); if not ch then return end
	for _, l in ipairs(ch:GetDescendants()) do
		if l:IsA("SpotLight") or l:IsA("PointLight") or l:IsA("SurfaceLight") then
			if actif then if l:GetAttribute("EteintParEncre") then l.Enabled = true; l:SetAttribute("EteintParEncre", nil) end
			elseif l.Enabled then l.Enabled = false; l:SetAttribute("EteintParEncre", true) end
		end
	end
end

-- étouffement vu par la victime : l'image s'assombrit et se décolore à mesure que la vie baisse, la caméra tremble à chaque serrement
local etouffe = { actif = false, debut = 0, cc = nil :: ColorCorrectionEffect?, flou = nil :: BlurEffect? }
local function etouffer(actif: boolean)
	if actif == etouffe.actif then return end
	etouffe.actif = actif
	if actif then
		etouffe.debut = os.clock()
		local cc = Instance.new("ColorCorrectionEffect"); cc.Name = "WitnessEtouffe"; cc.Parent = Lighting; etouffe.cc = cc
		local fl = Instance.new("BlurEffect"); fl.Name = "WitnessEtouffe"; fl.Size = 0; fl.Parent = Lighting; etouffe.flou = fl
		RunService:BindToRenderStep("WitnessEtouffe", Enum.RenderPriority.Camera.Value + 1, function()
			local ch = personnage(); local h = ch and ch:FindFirstChildOfClass("Humanoid")
			local manque = h and (1 - math.clamp(h.Health / math.max(h.MaxHealth, 1), 0, 1)) or 0
			local tt = os.clock() - etouffe.debut
			local serre = math.max(0, math.sin(tt * 7))
			if etouffe.cc then
				etouffe.cc.Brightness = -0.1 - 0.45 * manque - 0.08 * serre
				etouffe.cc.Saturation = -0.3 - 0.6 * manque
				etouffe.cc.TintColor = Color3.new(1, 1 - 0.25 * manque, 1 - 0.3 * manque)
			end
			if etouffe.flou then etouffe.flou.Size = 2 + 14 * manque + 4 * serre end
			noir.BackgroundTransparency = 1 - (0.15 + 0.6 * manque) * (0.85 + 0.15 * serre)
			local cam = workspace.CurrentCamera
			if cam then
				local a = 0.006 + 0.012 * serre
				cam.CFrame = cam.CFrame * CFrame.Angles(math.sin(tt * 31) * a, math.sin(tt * 23 + 1) * a, 0)
			end
		end)
	else
		RunService:UnbindFromRenderStep("WitnessEtouffe")
		if etouffe.cc then etouffe.cc:Destroy(); etouffe.cc = nil end
		if etouffe.flou then etouffe.flou:Destroy(); etouffe.flou = nil end
		noir.BackgroundTransparency = 1
	end
end

-- nuage d'encre : brume sombre qui gonfle, paillettes vertes lumineuses, nappe noire qui s'étale sur l'eau
local function nuageEncre(pos: Vector3, rayon: number, duree: number)
	local base = Instance.new("Part"); base.Anchored = true; base.CanCollide = false; base.CanQuery = false; base.CanTouch = false
	base.Transparency = 1; base.Size = Vector3.one; base.Position = pos + Vector3.new(0, 1, 0); base.Name = "Encre"; base.Parent = workspace
	local att = Instance.new("Attachment"); att.Parent = base
	local fumee = Instance.new("ParticleEmitter")
	fumee.Texture = "rbxasset://textures/particles/smoke_main.dds"; fumee.Enabled = false; fumee.Rate = 0
	fumee.Color = ColorSequence.new(Color3.fromRGB(12, 34, 32), Color3.fromRGB(4, 12, 12))
	fumee.LightInfluence = 1; fumee.LightEmission = 0
	fumee.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 2.5), NumberSequenceKeypoint.new(0.3, 7), NumberSequenceKeypoint.new(1, 11) })
	fumee.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.05), NumberSequenceKeypoint.new(0.7, 0.35), NumberSequenceKeypoint.new(1, 1) })
	fumee.Lifetime = NumberRange.new(duree * 0.8, duree + 1.5); fumee.Speed = NumberRange.new(10, 22); fumee.Drag = 2.2
	fumee.SpreadAngle = Vector2.new(180, 180); fumee.Acceleration = Vector3.new(0, 0.6, 0)
	fumee.Rotation = NumberRange.new(0, 360); fumee.RotSpeed = NumberRange.new(-20, 20); fumee.Parent = att
	local paillettes = Instance.new("ParticleEmitter")
	paillettes.Texture = "rbxasset://textures/particles/sparkles_main.dds"; paillettes.Enabled = false; paillettes.Rate = 0
	paillettes.Color = ColorSequence.new(Color3.fromRGB(100, 255, 160)); paillettes.LightEmission = 1; paillettes.LightInfluence = 0
	paillettes.Size = NumberSequence.new(0.25, 0.08)
	paillettes.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(0.8, 0.2), NumberSequenceKeypoint.new(1, 1) })
	paillettes.Lifetime = NumberRange.new(duree - 0.5, duree + 1); paillettes.Speed = NumberRange.new(6, 18); paillettes.Drag = 2.4
	paillettes.SpreadAngle = Vector2.new(180, 180); paillettes.Parent = att
	fumee:Emit(80); paillettes:Emit(180)
	local s = Eau.surface(pos, 3)
	if s then
		local nappe = Instance.new("Part"); nappe.Anchored = true; nappe.CanCollide = false; nappe.CanQuery = false; nappe.CanTouch = false
		nappe.Transparency = 1; nappe.Size = Vector3.new(2, 0.05, 2); nappe.CFrame = CFrame.new(pos.X, s + 0.04, pos.Z); nappe.Name = "NappeEncre"
		local sg = Instance.new("SurfaceGui"); sg.Face = Enum.NormalId.Top; sg.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
		sg.PixelsPerStud = 8; sg.LightInfluence = 1; sg.Parent = nappe
		local f = Instance.new("Frame"); f.Size = UDim2.fromScale(1, 1); f.BackgroundColor3 = Color3.fromRGB(5, 14, 14); f.BorderSizePixel = 0; f.Parent = sg
		local coin = Instance.new("UICorner"); coin.CornerRadius = UDim.new(0.5, 0); coin.Parent = f
		nappe.Parent = workspace
		task.spawn(function()
			local t0 = os.clock()
			while os.clock() - t0 < duree + 2.5 do
				local x = os.clock() - t0
				local d = 2 + (rayon * 2 - 2) * (1 - math.exp(-x / 0.45))
				nappe.Size = Vector3.new(d, 0.05, d)
				f.BackgroundTransparency = 0.2 + 0.8 * math.clamp((x - duree) / 2.5, 0, 1)
				task.wait()
			end
			nappe:Destroy()
		end)
	end
	task.delay(duree + 3, function() base:Destroy() end)
end

local debat
evEffet.OnClientEvent:Connect(function(quoi, a, b, c)
	local ch = personnage(); local h = ch and ch:FindFirstChildOfClass("Humanoid"); local r = ch and ch:FindFirstChild("HumanoidRootPart")
	if quoi == "recul" and r then
		r:ApplyImpulse(a * r.AssemblyMass * 12)
	elseif quoi == "renverse" and h then
		h:ChangeState(Enum.HumanoidStateType.FallingDown)
		task.delay(a or 1.5, function() if h.Parent then h:ChangeState(Enum.HumanoidStateType.GettingUp) end end)
	elseif quoi == "saisi" then
		aide.Text = "Débats-toi ! (ESPACE)"
		if a ~= "enlevement" then etouffer(true) end
		debat = UserInputService.InputBegan:Connect(function(io, traite)
			if not traite and (io.KeyCode == Enum.KeyCode.Space or io.KeyCode == Enum.KeyCode.ButtonA) then evDebat:FireServer() end
		end)
	elseif quoi == "englouti" then
		local duree = a or 2
		local cc = Instance.new("ColorCorrectionEffect"); cc.Parent = Lighting
		local fl = Instance.new("BlurEffect"); fl.Size = 0; fl.Parent = Lighting
		task.spawn(function()
			local t0 = os.clock()
			while os.clock() - t0 < duree + 0.3 do
				local u = math.clamp((os.clock() - t0) / duree, 0, 1)
				cc.TintColor = Color3.new(1 - 0.55 * u, 1 - 0.1 * u, 1 - 0.35 * u)
				cc.Brightness = -0.6 * u * u; cc.Saturation = -0.4 * u
				fl.Size = 6 + 20 * u
				noir.BackgroundTransparency = 1 - u * u
				task.wait()
			end
			cc:Destroy(); fl:Destroy()
		end)
	elseif quoi == "relache" then
		aide.Text = ""; if debat then debat:Disconnect(); debat = nil end
		etouffer(false)
	elseif quoi == "elimine" then
		aide.Text = ""; if debat then debat:Disconnect(); debat = nil end
		etouffer(false)
		if a == "devore" then noir.BackgroundTransparency = 0; son(r and r.Position or racine.Position, "morsure", 2)
		else for i = 1, 20 do noir.BackgroundTransparency = 1 - i / 20; task.wait(0.04) end end
		task.delay(4, function() noir.BackgroundTransparency = 1 end)
	elseif quoi == "encre" then
		local pos, rayon, duree = a, b, c
		nuageEncre(pos, rayon, duree)
		son(pos, "encre", 1.5)
		if r and (r.Position - pos).Magnitude < rayon then
			task.wait(math.min(0.6, (r.Position - pos).Magnitude / 20))          -- le nuage arrive jusqu'à lui
			local flou = Instance.new("BlurEffect"); flou.Size = 24; flou.Parent = Lighting
			local cc = Instance.new("ColorCorrectionEffect"); cc.TintColor = Color3.fromRGB(120, 255, 190); cc.Brightness = -0.15; cc.Parent = Lighting
			lumieresJoueur(false)
			task.delay(duree, function() flou:Destroy(); cc:Destroy(); lumieresJoueur(true) end)
		end
	elseif quoi == "coups" then
		local pos, rythme = a, b
		local delais = {}; for d in string.gmatch(rythme or "", "[^,]+") do table.insert(delais, tonumber(d) or 0.3) end
		son(pos, "coups", 1.2)
		for _, d in ipairs(delais) do task.wait(d); son(pos, "coups", 1.2) end
	elseif quoi == "pas" then
		local pos, _, duree = a, b, c
		local t0 = os.clock()
		while os.clock() - t0 < (duree or 4) do son(pos, "pas", 0.9); task.wait(0.42) end
	end
end)

-- faux message dans le chat de l'équipe : même apparence qu'un vrai message du joueur imité
evMessage.OnClientEvent:Connect(function(nom, hex, texte)
	local canaux = TextChatService:FindFirstChild("TextChannels")
	local general = canaux and canaux:FindFirstChild("RBXGeneral")
	local echappe = texte:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;")
	if general then general:DisplaySystemMessage(string.format("<font color=\"#%s\">%s:</font> %s", hex, nom, echappe)) end
end)
