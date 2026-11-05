--[[ THE WITNESS — corps (LocalScript, StarterPlayer > StarterPlayerScripts).
Chaque joueur affiche sa propre copie du modèle et l'anime os par os à partir de la pièce « WitnessRacine » déplacée par le serveur :
ondulation et marche des bras, respiration du manteau, regard qui suit le joueur, gestes d'attaque, lumières et imitations.
Gère aussi les effets reçus du serveur (recul, chute, saisie, encre, coups à la porte, faux pas, faux messages, élimination).
Modèle attendu : ReplicatedStorage > Witness > WitnessModele (import de witness.glb, squelette inclus). ]]

local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Lighting = game:GetService("Lighting")
local UP = Vector3.new(0, 1, 0)
local UserInputService = game:GetService("UserInputService")
local TextChatService = game:GetService("TextChatService")

local joueur = Players.LocalPlayer
local dossier = RS:WaitForChild("Witness")
local C = require(dossier:WaitForChild("WitnessConfig"))
local G = require(dossier:WaitForChild("WitnessGestes"))
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
	for _, k in ipairs({ 0, 7 }) do
		local chn = BRAS[k]
		if chn then
			local B = (parent * chn.os[1].CFrame).Position
			local sens = ((B - N):Dot(l) >= 0) and 1 or -1
			local pts = G.cheminEnroule(B, N, U, f, r, (k == 0) and 0.1 or 0.3, sens, tours)
			for j = 1, 8 do poids[j] = G.lisse((tt - 0.05 * (j - 1)) / 0.4) end
			G.orienter(chn, parent, G.articulations(B, pts, chn.L), poids)
		end
	end
	-- bras d'appui : vers le sol, en étoile autour d'elle
	local solY = racine.Position.Y
	local w = 0.9 * G.lisse(tt / 0.5)
	for j = 1, 8 do poids[j] = w end
	for k = 1, 6 do
		local chn = BRAS[k]
		if chn then
			local B = (parent * chn.os[1].CFrame).Position
			local dir = Vector3.new(B.X - centre.X, 0, B.Z - centre.Z); dir = dir.Magnitude > 1e-3 and dir.Unit or f
			local Fpt = Vector3.new(centre.X, solY, centre.Z) + dir * 4.2
			G.orienter(chn, parent, G.articulations(B, G.cheminSol(B, dir, Fpt, UP), chn.L), poids)
		end
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
local marcheEtat = G.nouvelleMarche()
local poidsLoco = 0
local P_POSE = { 1, 1, 1, 1, 1, 1, 0.75, 0.5 }       -- les pointes gardent leur enroulement
local P_COURSE = { 1, 1, 1, 1, 1, 1, 0.85, 0.7 }
local function locomotion(t: number, dt: number, actif: boolean)
	poidsLoco += ((actif and 1 or 0) - poidsLoco) * math.min(1, dt * 6)
	if poidsLoco < 0.01 or not osRacine then marcheEtat = G.nouvelleMarche(); return end
	local cf = cfAffiche
	local haut = cf.UpVector
	local vel = vitesseV - haut * vitesseV:Dot(haut)
	G.majMarche(marcheEtat, t, cf, DIRS, vel)
	local course = G.lisse((vel.Magnitude - G.MARCHE.course_debut) / (G.MARCHE.course_plein - G.MARCHE.course_debut))
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local avant = vel.Magnitude > 0.5 and vel.Unit or cf.RightVector       -- RightVector du repère affiché = avant du modèle (+X)
	local wp, wc = {}, {}
	for j = 1, 8 do wp[j] = P_POSE[j] * poidsLoco * (1 - course); wc[j] = P_COURSE[j] * poidsLoco * course end
	for k, chn in pairs(BRAS) do
		local B = (parent * chn.os[1].CFrame).Position
		if course < 0.999 then
			local F = G.pied(marcheEtat, k, t, haut)
			if F then G.orienter(chn, parent, G.articulations(B, G.cheminPied(B, F, centre, haut), chn.L), wp) end
		end
		if course > 0.001 then
			G.orienter(chn, parent, G.articulations(B, G.cheminTrainee(B, centre, avant, haut, t), chn.L), wc)
		end
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
-- décalage du corps affiché pendant une attaque (bond, bascule, tour sur elle-même), dans le repère du modèle
local function decalageGeste(coup: string?, e: number, signe: number): CFrame
	if coup == "fouet" and e < signe + G.FOUET.frappe + G.FOUET.retour then
		local T = cibleAttaque()
		local dist = T and horizontal(T - racine.Position).Magnitude or 0
		local _, _, corpsCF = G.fouet(e, signe, dist)
		return corpsCF
	elseif coup == "balayage" and e < signe + G.BALAYAGE.tour + 0.4 then
		local corpsCF = G.balayage(e, signe)
		return corpsCF
	elseif coup == "morsure" and e < signe + G.MORSURE.tenue + G.MORSURE.retour then
		local corpsCF = G.morsure(e, signe)
		return corpsCF
	end
	return CFrame.identity
end
local fouetBras = { coupT = -1, k = 0 }
local P_BALAYAGE = { 1, 1, 1, 1, 1, 1, 0.85, 0.7 }
local function gestesAttaque(coup: string?, e: number, signe: number, coupT: number)
	if not osRacine then return end
	local parent = mondeOs(osRacine)
	local centre = parent.Position
	local haut = cfAffiche.UpVector
	if coup == "fouet" and e < signe + G.FOUET.frappe + G.FOUET.retour then
		local T = cibleAttaque() or (centre + cfAffiche.RightVector * 9 - haut * 1)
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
		local global, frappe = G.fouet(e, signe, horizontal(T - centre).Magnitude)
		local loin = horizontal(B - T); loin = loin.Magnitude > 1e-3 and loin.Unit or -cfAffiche.RightVector
		local Ja = G.articulations(B, G.cheminFouetArme(B, loin, haut), chn.L)
		local Jf = G.articulations(B, G.cheminFouetFrappe(B, T), chn.L)
		local J, poids = {}, {}
		for j = 1, 8 do J[j] = Ja[j]:Lerp(Jf[j], frappe(j)); poids[j] = global end
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
	local marche = (mode == "mur") and math.clamp(v / 10, 0, 1) or 0
	local wg = math.min(2 + v * 0.5, 8)
	local becMorsure, ecartMorsure = 0, 0
	if coup == "morsure" then _, becMorsure, ecartMorsure = G.morsure(e, signe) end
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
			elseif coup == "balayage" then
				-- elle s'aplatit, pointes enroulées ; les bras tendus du tour sont posés plus bas (gestesAttaque)
				local a = (e < signe) and lisse(e / signe) or 1
				pitch += (j <= 2 and -0.1 or (j >= 6 and 0.3 or 0)) * a
			elseif coup == "morsure" and (k == 0 or k == 1 or k == 6 or k == 7) then
				-- les bras avant s'écartent pour dégager le bec
				yaw += ((k <= 1) and 1 or -1) * 0.5 * ecartMorsure * (j <= 2 and 1 or 0.3)
				pitch -= 0.1 * ecartMorsure
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
	ang(os_.Manteau1, 0.05 * respi + contraction, 0.02 * math.sin(t * 0.7))
	ang(os_.Manteau2, 0.08 * math.sin(t * 1.25 + 0.5) + contraction, 0.04 * math.sin(t * 0.6))
	ang(os_.Tete, -0.3 * ecartMorsure + 0.03 * math.sin(t * 0.8), 0)
	ang(os_.Bec, 0.6 * becMorsure, 0)
	-- marche : pieds posés au plafond et au sol, faisceau en course (hors gestes d'attaque, chute, saisie)
	local geste = saisie or chuteEtat.phase ~= "" or (coup ~= nil and coup ~= "avorte" and e < signe + 0.8)
		or etat == "morte" or etat == "etourdie"
	locomotion(t, dt, not geste and (mode == "plafond" or mode == "sol"))
	-- attaques au contact : bras du fouet, bras tendus du balayage
	gestesAttaque(coup, e, signe, coupT)
	-- saisie : les deux bras avant s'enroulent autour du cou (ou du torse pour un enlèvement), les autres prennent appui au sol
	if saisie then enrouler(t) end
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
		if etat == "morte" then tr = 1
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
	halo.Enabled = etat ~= "morte" and not eteinte
	halo.Brightness = (imitation == "voyants") and 1.2 or 0.5
	halo.Color = (imitation == "voyants") and Color3.fromRGB(255, 70, 50) or Color3.fromRGB(86, 224, 208)
	fausseLampe.Brightness = (imitation == "lampe" and etat ~= "morte") and 3 or 0
	-- mort : le verre devient laiteux et opaque
	for _, p in ipairs(verre) do
		if etat == "morte" then p.Material = Enum.Material.SmoothPlastic; p.Transparency = 0.12; p.Color = Color3.fromRGB(230, 232, 228) end
		local brule = maintenant < (racine:GetAttribute("Brule") or 0)
		if brule and etat ~= "morte" then p.Color = Color3.fromRGB(255, 150, 90) elseif etat ~= "morte" then p.Color = Color3.fromRGB(216, 236, 240) end
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
	if coup == "descente" and typeof(depart) == "Vector3" and e < d + tf + C.ATTERRISSAGE then
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
	else
		chuteEtat.phase = ""
		if racine:GetAttribute("Saisie") and racine:GetAttribute("SaisieType") ~= "enlevement" then
			cible = cible * G.cabrer(workspace:GetServerTimeNow() - (racine:GetAttribute("SaisieT") or 0))
		end
		cfAffiche = cfAffiche:Lerp(cible, 1 - math.exp(-14 * dt))
	end
	local coupG = racine:GetAttribute("Coup")
	local signeG = coupG and C.COUPS[coupG] and C.COUPS[coupG].signe or 0.5
	corps:PivotTo(cfAffiche * decalageGeste(coupG, workspace:GetServerTimeNow() - (racine:GetAttribute("CoupT") or 0), signeG))
	-- vitesse du corps affiché (lissé) : sert à la marche à pieds posés
	vitesseV = vitesseV:Lerp((cfAffiche.Position - avantAff) / math.max(dt, 1e-3), math.min(1, dt * 10))
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
		local nuage = Instance.new("Part"); nuage.Anchored = true; nuage.CanCollide = false; nuage.CanQuery = false; nuage.Transparency = 1
		nuage.Size = Vector3.one; nuage.Position = pos; nuage.Parent = workspace
		local pe = Instance.new("ParticleEmitter"); pe.Color = ColorSequence.new(Color3.fromRGB(40, 255, 160), Color3.fromRGB(10, 40, 30))
		pe.LightEmission = 0.6; pe.Size = NumberSequence.new(4, 9); pe.Transparency = NumberSequence.new(0.3, 1); pe.Lifetime = NumberRange.new(2, 4)
		pe.Rate = 60; pe.Speed = NumberRange.new(4, 9); pe.SpreadAngle = Vector2.new(180, 180); pe.Parent = nuage
		task.delay(0.6, function() pe.Enabled = false end); task.delay(duree + 4, function() nuage:Destroy() end)
		son(pos, "encre", 1.5)
		if r and (r.Position - pos).Magnitude < rayon then
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
