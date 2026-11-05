--[[ THE WITNESS — cerveau (Script, ServerScriptService).
Perception, jauges de suspicion, phases, machine à états, déplacements sur le réseau plafonds/gaines, course au sol,
attaques, points de vie, feu, imitations. Le corps visible est animé par chaque joueur (WitnessCorps) à partir de la
pièce invisible « WitnessRacine » que ce script déplace et de ses attributs.

Points d'entrée pour les autres systèmes du jeu (ReplicatedStorage > Witness) :
  WitnessBruit (BindableEvent)   :Fire(position, force)            bruit (porte, objet tombé, cri) ; force 1 = normal
  WitnessDegats (BindableEvent)  :Fire(montant, "feu"|"normal", joueur)
  WitnessCapture (BindableEvent) :Fire(joueur)                      tentative de capture (outil des classes)
  WitnessPorte (BindableEvent)   émis quand elle ouvre une porte à badge : (position, typePorte)
Attributs lus sur ReplicatedStorage : Preuves (nombre), Implosion (booléen) ; BoolValue « Courant ».
Pièces taguées « Feu » (CollectionService) : sources de feu qu'elle fuit. ]]

local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local PathfindingService = game:GetService("PathfindingService")
local CollectionService = game:GetService("CollectionService")

local dossier = RS:WaitForChild("Witness")
local C = require(dossier:WaitForChild("WitnessConfig"))
local Nav = require(dossier:WaitForChild("WitnessNav")).new(require(dossier:WaitForChild("NavWitness")))
local Eau = require(dossier:WaitForChild("WitnessEau"))

local function obtenir(nom, classe)
	local o = dossier:FindFirstChild(nom)
	if not o then o = Instance.new(classe); o.Name = nom; o.Parent = dossier end
	return o
end
local evEffet = obtenir("WitnessEffet", "RemoteEvent")      -- serveur -> joueur : effets d'écran, recul, encre, coups, pas
local evRegard = obtenir("WitnessRegard", "RemoteEvent")    -- joueur -> serveur : direction du regard, lumières fixées
local evDebat = obtenir("WitnessDebat", "RemoteEvent")      -- joueur -> serveur : se débattre
local evMessage = obtenir("WitnessMessage", "RemoteEvent")  -- serveur -> joueur : faux message dans le chat
local bBruit = obtenir("WitnessBruit", "BindableEvent")
local bDegats = obtenir("WitnessDegats", "BindableEvent")
local bCapture = obtenir("WitnessCapture", "BindableEvent")
local bPorte = obtenir("WitnessPorte", "BindableEvent")

local UP = Vector3.new(0, 1, 0)

-- ================================================================ la pièce racine (position et orientation de la créature)
local racine = workspace:FindFirstChild("WitnessRacine") or Instance.new("Part")
racine.Name = "WitnessRacine"; racine.Anchored = true; racine.CanCollide = false; racine.CanTouch = false; racine.CanQuery = true
racine.CastShadow = false; racine.Transparency = 1; racine.Size = C.TAILLE_CORPS; racine.Parent = workspace

-- ================================================================ état
local W = {
	pos = Vector3.zero, avant = Vector3.new(1, 0, 0), mode = "plafond", etat = "rode", phase = 1, debut = os.clock(),
	chemin = nil, etape = 1, noeud = nil, occupe = false, cible = nil, jauge = {}, regard = {}, debats = {},
	dernierSignal = nil, dernierVu = {}, cachettes = {}, recharges = {}, solDebut = 0, solFin = -100,
	pv = C.PV_BASE, pvMax = C.PV_BASE, paliers = {}, degatsRecents = {}, brulure = 0, saisie = nil, premierMort = false,
	fixeeJusqua = 0, etatDepuis = os.clock(), imitationJusqua = 0, historiqueChat = {}, virageJusqua = 0,
}

local function regler(etat)
	if W.etat ~= etat then W.etat = etat; W.etatDepuis = os.clock(); racine:SetAttribute("Etat", etat) end
end
local function joueursVivants()
	local t = {}
	for _, p in ipairs(Players:GetPlayers()) do
		local ch = p.Character; local h = ch and ch:FindFirstChildOfClass("Humanoid")
		if h and h.Health > 0 and ch:FindFirstChild("HumanoidRootPart") then table.insert(t, p) end
	end
	return t
end
local function hrp(p) return p.Character and p.Character:FindFirstChild("HumanoidRootPart") end
local function tete(p) return p.Character and p.Character:FindFirstChild("Head") end
local function humanoide(p) return p.Character and p.Character:FindFirstChildOfClass("Humanoid") end
local function courant() local v = RS:FindFirstChild("Courant"); if not v then return true end; return v.Value == true end   -- sans BoolValue : courant présent

local function initialiserPV()
	local n = math.max(1, #Players:GetPlayers())
	W.pvMax = C.PV_BASE + C.PV_PAR_JOUEUR * (n - 1); W.pv = W.pvMax
	racine:SetAttribute("PVMax", W.pvMax); racine:SetAttribute("PV", W.pv)
end

-- ================================================================ perception
local params = RaycastParams.new(); params.FilterType = Enum.RaycastFilterType.Exclude
local function filtreVue()
	local ex = { racine }
	for _, p in ipairs(Players:GetPlayers()) do if p.Character then table.insert(ex, p.Character) end end
	local corps = workspace:FindFirstChild("WitnessCorps"); if corps then table.insert(ex, corps) end
	params.FilterDescendantsInstances = ex
end
local function oeil()
	return W.pos + (W.mode == "plafond" and -UP * 1.5 or UP * 1.5)
end
local function ligneDeVue(p)
	local t = tete(p); if not t then return false end
	local o = oeil(); local d = t.Position - o
	if d.Magnitude > 140 then return false end
	local regard = (W.mode == "plafond") and -UP or W.avant
	if W.mode ~= "gaine" and d.Unit:Dot(regard) < math.cos(math.rad(C.VISION_ANGLE / 2)) then return false end
	if W.mode == "gaine" then return false end          -- dans les gaines : l'ouïe seulement (les grilles laissent passer le son)
	return workspace:Raycast(o, d, params) == nil
end
local function lampeAllumee(p)
	local ch = p.Character; if not ch then return false, nil end
	for _, l in ipairs(ch:GetDescendants()) do
		if (l:IsA("SpotLight") or l:IsA("SurfaceLight") or l:IsA("PointLight")) and l.Enabled and l.Brightness > 0.2 then
			local part = l.Parent
			return true, (part and part:IsA("BasePart")) and part.CFrame.LookVector or nil
		end
	end
	return false, nil
end
local function coequipierProche(p, rayon)
	local r = hrp(p); if not r then return false end
	for _, q in ipairs(joueursVivants()) do
		if q ~= p then local s = hrp(q); if s and (s.Position - r.Position).Magnitude < rayon then return true end end
	end
	return false
end

local function signaler(pos) W.dernierSignal = { pos = pos, t = os.clock() } end

local function percevoir(dt)
	filtreVue()
	local J = C.JAUGE; local lumiere = courant()
	for _, p in ipairs(joueursVivants()) do
		local r, t = hrp(p), tete(p)
		if not (r and t) then continue end
		local dist = (t.Position - oeil()).Magnitude
		local vit = Vector3.new(r.AssemblyLinearVelocity.X, 0, r.AssemblyLinearVelocity.Z).Magnitude
		local vu = ligneDeVue(p)
		local lampe, dirLampe = lampeAllumee(p)
		local gain = 0
		if dist < C.PROCHE then gain += J.proche end
		if vu then
			W.dernierVu[p] = os.clock()
			if lampe and dist < J.lampe_portee then
				if dirLampe and dirLampe:Dot((oeil() - t.Position).Unit) > 0.94 then W.jauge[p] = J.chasse
				else gain += J.lampe_vue end
			end
			if lumiere and vit > 2 and dist < J.lumiere_portee then gain += J.lumiere_bouge
			elseif not lumiere then
				if vit > 2 and dist < J.noir_marche_portee then gain += J.noir_marche
				elseif dist < J.noir_immobile_portee then gain += J.noir_immobile end
			end
		end
		if vit > 15 and dist < J.course_portee then gain += J.course end
		-- bouger dans l'eau s'entend, selon l'allure : sprint (fort), marche (léger), accroupi (rien)
		local allure = C.allure(p, vit)
		if allure and allure ~= "accroupi" and p.Character and Eau.pieds(p.Character) then
			local b = C.EAU[allure]
			if b and dist < b.portee then gain += b.bruit end
		end
		if gain > 0 and not coequipierProche(p, J.seul_rayon) then gain *= J.seul_mult end
		local avant = W.jauge[p] or 0
		local apres = gain > 0 and math.min(J.chasse, avant + gain * dt) or math.max(0, avant - J.baisse * dt)
		if gain > 0 then signaler(r.Position) end
		-- un joueur qui « tient » sa cachette pendant une fouille : elle s'en souviendra
		if W.etat == "fouille" and avant >= J.fouille and apres < J.fouille then table.insert(W.cachettes, r.Position) end
		W.jauge[p] = apres
	end
	for p in pairs(W.jauge) do if not p.Parent then W.jauge[p] = nil end end
end

bBruit.Event:Connect(function(pos, force)
	force = force or 1
	for _, p in ipairs(joueursVivants()) do
		local r = hrp(p)
		if r and (r.Position - pos).Magnitude < 8 and (pos - W.pos).Magnitude < C.JAUGE.bruit_portee * force then
			W.jauge[p] = math.min(C.JAUGE.chasse, (W.jauge[p] or 0) + C.JAUGE.bruit * force)
		end
	end
	if (pos - W.pos).Magnitude < C.JAUGE.bruit_portee * force then signaler(pos) end
end)

local function brancherChat(p)
	p.Chatted:Connect(function(msg)
		W.historiqueChat[p.UserId] = W.historiqueChat[p.UserId] or {}
		local h = W.historiqueChat[p.UserId]; table.insert(h, msg); if #h > 25 then table.remove(h, 1) end
		local r = hrp(p)
		if r and (r.Position - W.pos).Magnitude < C.JAUGE.chat_portee then
			W.jauge[p] = math.min(C.JAUGE.chasse, (W.jauge[p] or 0) + C.JAUGE.chat); signaler(r.Position)
		end
	end)
	p.CharacterAdded:Connect(function(ch)
		local h = ch:WaitForChild("Humanoid")
		h.Died:Connect(function() if not W.premierMort then W.premierMort = true end end)
	end)
end
for _, p in ipairs(Players:GetPlayers()) do brancherChat(p) end
Players.PlayerAdded:Connect(brancherChat)

evRegard.OnServerEvent:Connect(function(p, regard, fixe)
	if typeof(regard) ~= "Vector3" then return end
	W.regard[p] = regard
	if fixe and os.clock() > W.fixeeJusqua and (W.etat == "rode" or W.etat == "fouille") then
		W.fixeeJusqua = os.clock() + 6; racine:SetAttribute("Eteinte", workspace:GetServerTimeNow() + 3)
		W.chemin = nil; W.forcerDeplacement = true               -- elle sait qu'elle est vue : elle change de place
	end
end)
evDebat.OnServerEvent:Connect(function(p) W.debats[p] = (W.debats[p] or 0) + 1 end)

-- ================================================================ phases
local function majPhase()
	local t = os.clock() - W.debut; local preuves = RS:GetAttribute("Preuves") or 0
	local ph = W.phase; local P = C.PHASES
	if ph < 2 and (t >= P[2].temps or preuves >= P[2].preuves) then ph = 2 end
	if ph < 3 and (t >= P[3].temps or preuves >= P[3].preuves or W.premierMort) then ph = 3 end
	if ph < 4 and (W.pv <= W.pvMax * (1 - P[4].pv_perdus) or RS:GetAttribute("Implosion")) then ph = 4 end
	if ph ~= W.phase then W.phase = ph; racine:SetAttribute("Phase", ph) end
end

-- ================================================================ déplacements
local function orienter(dir, plafond)
	if dir.Magnitude < 1e-3 then dir = W.avant end
	local horiz = Vector3.new(dir.X, 0, dir.Z)
	if W.mode ~= "gaine" and horiz.Magnitude > 1e-3 then dir = horiz.Unit end
	W.avant = dir.Unit
	local up = plafond and -UP or UP
	if math.abs(W.avant:Dot(up)) > 0.98 then return CFrame.new(W.pos) end
	return CFrame.lookAt(W.pos, W.pos + W.avant, up)
end
local function placer()
	racine.CFrame = orienter(W.avant, W.mode == "plafond")
	racine:SetAttribute("Mode", W.mode)
end
local function vitesse()
	local v = C.VITESSE[W.mode] or 14
	if W.mode == "plafond" and (W.etat == "chasse" or W.phase == 4) then v = C.VITESSE.plafond_pointe end
	return v
end
-- déplacement interpolé (bloquant) d'un point à un autre en t secondes, en changeant de mode à la fin
local function glisser(vers, duree, modeFin, plafondPendant)
	local de = W.pos; local t0 = os.clock()
	while true do
		local a = math.min(1, (os.clock() - t0) / duree)
		local e = a * a * (3 - 2 * a)
		W.pos = de:Lerp(vers, e)
		racine.CFrame = orienter(W.avant, plafondPendant)
		if a >= 1 then break end
		RunService.Heartbeat:Wait()
	end
	if modeFin then W.mode = modeFin end
	placer()
end

local function sonEn(pos, nom, volume)
	local id = C.SONS[nom]; if not id or id == "" then return end
	local a = Instance.new("Attachment"); a.WorldPosition = pos; a.Parent = workspace.Terrain
	local s = Instance.new("Sound"); s.SoundId = id; s.Volume = volume or 1; s.RollOffMaxDistance = 80; s.Parent = a; s:Play()
	task.delay(8, function() a:Destroy() end)
end

local function evitementFeu(i, j, t)
	local p = Nav:position(j)
	for _, f in ipairs(CollectionService:GetTagged("Feu")) do
		if f:IsA("BasePart") and (f.Position - p).Magnitude < C.PEUR_FEU then return 30 end
	end
	return 0
end

local function allerVers(posCible, couche)
	local a = W.noeud or Nav:plusProche(W.pos, nil, 128)
	local b = Nav:plusProche(posCible, couche, 128)
	local ch = Nav:chemin(a, b, { cout = W.phase < 4 and evitementFeu or nil })
	if ch then W.chemin = ch; W.etape = 2 end
	return ch ~= nil
end

local function franchirArete(et)
	if et.type == "grille" then
		W.occupe = true
		sonEn(et.passage or et.pos, "succion")
		racine:SetAttribute("Passage", os.clock())
		local versGaine = Nav:estGaine(et.noeud)
		glisser(et.passage or et.pos, C.GRILLE_PASSAGE * 0.5, nil, not versGaine)
		W.mode = versGaine and "gaine" or "plafond"
		glisser(et.pos + (versGaine and -UP * 2.3 or Vector3.zero), C.GRILLE_PASSAGE * 0.5, W.mode, W.mode == "plafond")
		W.occupe = false
	elseif et.type == "porte" and et.passage then
		W.occupe = true; W.mode = "mur"
		glisser(et.passage, ((et.passage - W.pos).Magnitude) / C.VITESSE.mur, nil, false)
		if et.porte and string.find(et.porte, "badge") then
			bPorte:Fire(et.passage, et.porte); sonEn(et.passage, "bip")
			local reg = RS:GetAttribute("RegistreBadges") or ""
			RS:SetAttribute("RegistreBadges", reg .. string.format("%s;ALDANE I.\n", os.date("!%H:%M:%S")))
		end
		glisser(et.pos, ((et.pos - W.pos).Magnitude) / C.VITESSE.mur, "plafond", true)
		W.occupe = false
	end
end

local function suivreChemin(dt)
	local ch = W.chemin; if not ch then return true end
	local et = ch[W.etape]; if not et then W.chemin = nil; return true end
	if et.type == "grille" or (et.type == "porte" and et.passage) then
		task.spawn(function() franchirArete(et); W.noeud = et.noeud; W.etape += 1 end)
		return false
	end
	local cible = et.pos + (Nav:estGaine(et.noeud) and -UP * 2.3 or Vector3.new(0, 0.3, 0))
	local d = cible - W.pos
	local pas = vitesse() * dt
	if d.Magnitude <= pas then
		W.pos = cible; W.noeud = et.noeud; W.etape += 1
		W.mode = Nav:estGaine(et.noeud) and "gaine" or "plafond"
	else
		W.pos += d.Unit * pas; W.avant = d.Unit
	end
	placer()
	return false
end

-- course au sol (recherche de chemin Roblox)
local solChemin, solCibleT = nil, 0
local function solPoint(p)
	local r = workspace:Raycast(p + UP * 2, -UP * 60, params)
	return r and r.Position or p
end
--[[ se laisser tomber du plafond, en trois temps partagés avec les clients (attributs Chute*) :
décrochage (elle reste accrochée par l'arrière), chute libre avec la gravité du jeu, atterrissage. Bloquant. ]]
local function tomber(sol, decrochage)
	local depart = W.pos
	local h = math.max(0.5, depart.Y - sol.Y)
	local g = workspace.Gravity
	local tf = math.sqrt(2 * h / g)
	racine:SetAttribute("ChuteDepart", depart); racine:SetAttribute("ChuteSol", sol)
	racine:SetAttribute("ChuteDecroche", decrochage); racine:SetAttribute("ChuteTf", tf)
	racine:SetAttribute("Coup", "descente"); racine:SetAttribute("CoupT", workspace:GetServerTimeNow())
	task.wait(decrochage)
	local t0 = os.clock()
	while true do
		local a = math.min(tf, os.clock() - t0)
		local u = a / tf
		W.pos = Vector3.new(depart.X + (sol.X - depart.X) * u, depart.Y - 0.5 * g * a * a, depart.Z + (sol.Z - depart.Z) * u)
		racine.CFrame = orienter(W.avant, false)
		if a >= tf then break end
		RunService.Heartbeat:Wait()
	end
	W.pos = sol; W.mode = "sol"; placer(); sonEn(sol, "chute")
	task.wait(C.ATTERRISSAGE)
end
local function descendre()
	W.occupe = true
	sonEn(W.pos, "goutte")
	tomber(solPoint(W.pos - UP * 3), C.DECROCHAGE)
	W.solDebut = os.clock(); W.noeud = nil; W.chemin = nil
	W.occupe = false
end
local function remonter()
	W.occupe = true
	local n = Nav:plusProche(W.pos, 1, 128)
	if n then
		W.mode = "mur"
		local p = Nav:position(n) + Vector3.new(0, 0.3, 0)
		glisser(Vector3.new(W.pos.X, p.Y, W.pos.Z), C.MONTEE_DUREE, "plafond", true)
		W.noeud = nil
	end
	W.solFin = os.clock(); W.occupe = false
end
local function courirVers(cible, dt)
	if os.clock() - solCibleT > 0.4 or not solChemin then
		solCibleT = os.clock()
		local path = PathfindingService:CreatePath({ AgentRadius = 2.5, AgentHeight = 3, AgentCanJump = false })
		local ok = pcall(function() path:ComputeAsync(W.pos, cible) end)
		solChemin = (ok and path.Status == Enum.PathStatus.Success) and path:GetWaypoints() or nil
		W.solEtape = 2
	end
	local wp = solChemin and solChemin[W.solEtape]
	local but = wp and wp.Position or cible
	local d = Vector3.new(but.X - W.pos.X, 0, but.Z - W.pos.Z)
	local v = C.VITESSE.sol
	if W.virageJusqua and os.clock() < W.virageJusqua then v = C.VIRAGE_LENT end
	if d.Magnitude < 1 then W.solEtape = (W.solEtape or 2) + 1; return end
	if W.avant:Dot(d.Unit) < 0.5 then W.virageJusqua = os.clock() + 0.5 end
	W.pos += d.Unit * math.min(d.Magnitude, v * dt)
	W.pos = solPoint(W.pos); W.avant = d.Unit
	placer()
end

-- ================================================================ attaques
local function effet(p, quoi, ...) if p and p.Parent then evEffet:FireClient(p, quoi, ...) end end
local function signe(coup)
	racine:SetAttribute("Coup", coup); racine:SetAttribute("CoupT", workspace:GetServerTimeNow())
	task.wait(C.COUPS[coup].signe or 0.5)
end
local function pret(coup) return os.clock() >= (W.recharges[coup] or 0) and W.phase >= C.COUPS[coup].phase end
local function recharger(coup) W.recharges[coup] = os.clock() + (C.COUPS[coup].recharge or 0) end
local function blesser(p, n, renverse, recul)
	local h = humanoide(p); if not h or h.Health <= 0 then return end
	h:TakeDamage(n)
	if recul then effet(p, "recul", recul) end
	if renverse then effet(p, "renverse", renverse) end
end
local function eliminer(p, comment)
	local h = humanoide(p); if not h then return end
	effet(p, "elimine", comment); h.Health = 0
end

local function relacher()
	local s = W.saisie; if not s then return end
	local r = hrp(s.victime); if r then r.Anchored = false end
	effet(s.victime, "relache"); W.saisie = nil
end

local function coupFouet(p)
	signe("fouet")
	local r = hrp(p)
	if r and (r.Position - W.pos).Magnitude <= C.COUPS.fouet.portee + 1 then
		blesser(p, C.COUPS.fouet.degats, nil, (r.Position - W.pos).Unit * C.COUPS.fouet.recul)
	end
	recharger("fouet")
end
local function coupBalayage()
	signe("balayage")
	for _, q in ipairs(joueursVivants()) do
		local r = hrp(q)
		if r and (r.Position - W.pos).Magnitude <= C.COUPS.balayage.portee then blesser(q, C.COUPS.balayage.degats, C.COUPS.balayage.renverse) end
	end
	recharger("balayage")
end
local function coupMorsure(p)
	signe("morsure")
	local r = hrp(p)
	if r and (r.Position - W.pos).Magnitude <= C.COUPS.morsure.portee + 1 then blesser(p, C.COUPS.morsure.degats) end
	recharger("morsure")
end
-- saisie : la victime est soulevée et étranglée ; libérée si l'équipe inflige assez de dégâts ou utilise le feu
local function coupSaisie(p, versGrille)
	signe(versGrille and "enlevement" or "saisie")
	local r = hrp(p); if not r or (r.Position - W.pos).Magnitude > C.COUPS.saisie.portee + 1 then recharger("saisie"); return end
	W.saisie = { victime = p, degats = 0, debut = os.clock(), feu = false }
	W.debats[p] = 0
	r.Anchored = true; effet(p, "saisi", versGrille and "enlevement" or "saisie")
	local versVictime = Vector3.new(r.Position.X - W.pos.X, 0, r.Position.Z - W.pos.Z)
	if versVictime.Magnitude > 0.1 then W.avant = versVictime.Unit; placer() end        -- elle fait face à sa proie
	racine:SetAttribute("Saisie", p.UserId); racine:SetAttribute("SaisieT", workspace:GetServerTimeNow())
	racine:SetAttribute("SaisieType", versGrille and "enlevement" or "saisie")
	local duree = math.random() * (C.COUPS.saisie.duree_max - C.COUPS.saisie.duree_min) + C.COUPS.saisie.duree_min
	local depart = W.pos
	while W.saisie and W.saisie.victime == p do
		local dt = RunService.Heartbeat:Wait()
		local h = humanoide(p); if not h or h.Health <= 0 then break end
		local seuil = versGrille and C.COUPS.enlevement.liberation or C.COUPS.saisie.liberation
		if W.saisie.degats >= seuil or W.saisie.feu or W.etat == "etourdie" then break end
		local tt = os.clock() - W.saisie.debut
		if versGrille then
			local g = versGrille
			local a = math.min(1, tt / C.COUPS.enlevement.trainee)
			W.pos = depart:Lerp(Vector3.new(g.X, W.pos.Y, g.Z), a); placer()
			r.CFrame = CFrame.new(W.pos + W.avant * 2 + UP * 1.5)
			if a >= 1 then
				eliminer(p, "enleve")
				local corps = p.Character
				task.delay(0.1, function() if corps and corps.Parent then corps:PivotTo(CFrame.new(g + UP * 3)) end end)
				break
			end
		else
			local deb = (W.debats[p] or 0) > 0 and 0.5 or 1; W.debats[p] = math.max(0, (W.debats[p] or 0) - dt * 4)
			h:TakeDamage(C.COUPS.saisie.dps * deb * dt)
			-- soulevée en 0,8 s, face à elle, puis secouée à chaque serrement
			local lev = math.min(1, tt / 0.8); lev = lev * lev * (3 - 2 * lev)
			local secousse = 0.08 * math.sin(tt * 7)
			local pos = W.pos + W.avant * C.SAISIE_DEVANT + UP * (3 + (C.SAISIE_HAUTEUR - 3) * lev + secousse)
			r.CFrame = CFrame.lookAt(pos, pos - W.avant)
			if tt > duree then eliminer(p, "etrangle"); break end
		end
	end
	racine:SetAttribute("Saisie", nil)
	relacher()
	recharger("saisie")
end
local function coupChute(p)
	signe("chute")
	local r = hrp(p); if not r then return end
	local regard = W.regard[p]; local lampe = lampeAllumee(p)
	if regard and regard.Y > 0.6 and lampe then              -- elle est vue : elle avorte et s'enfuit
		racine:SetAttribute("Coup", "avorte"); W.forcerFuite = true; return
	end
	local h = Vector3.new(r.Position.X - W.pos.X, 0, r.Position.Z - W.pos.Z).Magnitude
	if h <= C.COUPS.chute.rayon + 0.5 then
		local sol = solPoint(r.Position)
		tomber(sol, C.DECROCHAGE_EMBUSCADE)
		eliminer(p, "devore")
		task.wait(1.2)
	end
end
local function coupEncre()
	signe("encre")
	evEffet:FireAllClients("encre", W.pos, C.COUPS.encre.rayon, C.COUPS.encre.duree)
	recharger("encre")
end

-- choix du coup selon la situation (document : « Choix du coup »)
local function grilleProche(rayon)
	local best, bd = nil, rayon
	for _, g in ipairs(Nav.grilles) do
		if not g.soudee then
			local d = (Vector3.new(g.x, W.pos.Y, g.z) - W.pos).Magnitude
			if d < bd then best, bd = Vector3.new(g.x, g.y, g.z), d end
		end
	end
	return best
end
local function attaquer(p)
	W.occupe = true; regler("attaque")
	local r = hrp(p); local dist = r and (r.Position - W.pos).Magnitude or 99
	local seul = not coequipierProche(p, C.JAUGE.seul_rayon)
	local renverse = r and humanoide(p) and humanoide(p):GetState() == Enum.HumanoidStateType.FallingDown
	local horiz = r and Vector3.new(r.Position.X - W.pos.X, 0, r.Position.Z - W.pos.Z).Magnitude or 99
	local groupe = 0
	for _, q in ipairs(joueursVivants()) do local s = hrp(q); if s and (s.Position - W.pos).Magnitude < 10 then groupe += 1 end end
	if W.mode == "plafond" and horiz <= C.COUPS.chute.rayon and seul and pret("chute") then coupChute(p)
	elseif W.mode == "sol" and groupe >= 2 and pret("balayage") then coupBalayage()
	elseif renverse and dist <= C.COUPS.morsure.portee + 1 and pret("morsure") then coupMorsure(p)
	elseif W.phase >= 3 and grilleProche(C.COUPS.enlevement.portee_grille) and dist <= C.COUPS.saisie.portee and pret("enlevement") then coupSaisie(p, grilleProche(C.COUPS.enlevement.portee_grille))
	elseif W.mode == "sol" and dist <= C.COUPS.saisie.portee and pret("saisie") then coupSaisie(p, nil)
	elseif dist <= C.COUPS.fouet.portee and pret("fouet") then coupFouet(p)
	end
	racine:SetAttribute("Coup", nil)
	local h = humanoide(p)
	if not h or h.Health <= 0 then
		if W.phase < 4 and math.random() < C.REPLI_APRES_ELIMINATION then regler("repli") else regler("chasse") end
	else
		regler("chasse")
	end
	W.occupe = false
end

-- ================================================================ points de vie, feu, étourdissement, capture
local function etourdir()
	if W.etat == "etourdie" or W.etat == "morte" then return end
	relacher(); regler("etourdie"); W.chemin = nil
	if W.pv <= W.pvMax * C.CAPTURE_PV then
		racine:SetAttribute("Capturable", true)
		task.delay(C.CAPTURE_FENETRE, function() racine:SetAttribute("Capturable", false) end)
	end
	task.delay(C.ETOURDI_DUREE, function() if W.etat == "etourdie" then regler("repli") end end)
end
local function mourir()
	regler("morte"); relacher(); W.chemin = nil
	racine:SetAttribute("PV", 0); racine.Name = "DepouilleWitness"
	if W.mode ~= "sol" then task.spawn(function() glisser(solPoint(W.pos - UP * 3), 0.8, "sol", false) end) end
end
bDegats.Event:Connect(function(montant, typ, joueur)
	if W.etat == "morte" or W.etat == "capturee" then return end
	local feu = typ == "feu"
	local n = montant * (feu and C.MULT_FEU or (typ == "brulure" and 1 or C.MULT_ORDINAIRE))
	W.pv = math.max(0, W.pv - n); racine:SetAttribute("PV", W.pv)
	if W.saisie then W.saisie.degats += montant; if feu then W.saisie.feu = true end end
	table.insert(W.degatsRecents, { os.clock(), n })
	if feu then
		W.brulure = os.clock() + C.BRULURE_DUREE; racine:SetAttribute("Brule", workspace:GetServerTimeNow() + C.BRULURE_DUREE)
		if W.phase < 4 then W.forcerFuite = true end
	end
	if joueur then local r = hrp(joueur); if r then signaler(r.Position); W.jauge[joueur] = C.JAUGE.chasse end end
	if W.pv <= 0 then mourir(); return end
	-- étourdissement : 15 % des PV en moins de 4 s, ou feu pendant un passage de grille
	local somme, t = 0, os.clock()
	for i = #W.degatsRecents, 1, -1 do
		if t - W.degatsRecents[i][1] > C.ETOURDI_FENETRE then table.remove(W.degatsRecents, i) else somme += W.degatsRecents[i][2] end
	end
	local enPassage = (os.clock() - (racine:GetAttribute("Passage") or 0)) < C.GRILLE_PASSAGE
	if somme >= W.pvMax * C.ETOURDI_SEUIL or (feu and enPassage) then etourdir(); return end
	for _, s in ipairs(C.PALIERS_FUITE) do
		if W.pv <= W.pvMax * s and not W.paliers[s] then W.paliers[s] = true; W.forcerFuite = true end
	end
end)
bCapture.Event:Connect(function(joueur)
	if racine:GetAttribute("Capturable") and W.etat == "etourdie" then regler("capturee"); racine:SetAttribute("Capturee", true) end
end)

-- ================================================================ imitations
local NOM_COULEURS = { Color3.fromRGB(253, 41, 67), Color3.fromRGB(1, 162, 255), Color3.fromRGB(2, 184, 87), BrickColor.new("Bright violet").Color,
	BrickColor.new("Bright orange").Color, BrickColor.new("Bright yellow").Color, BrickColor.new("Light reddish violet").Color, BrickColor.new("Brick yellow").Color }
local function couleurNom(nom)       -- couleur de pseudo du chat Roblox (même calcul que le chat par défaut)
	local v = 0
	for i = 1, #nom do
		local c = string.byte(nom, i); local ri = #nom - i + 1
		if #nom % 2 == 1 then ri -= 1 end
		if ri % 4 >= 2 then c = -c end
		v += c
	end
	return NOM_COULEURS[(v % #NOM_COULEURS) + 1]
end
local function imiter(cible)
	if os.clock() < W.imitationJusqua or not cible then return end
	W.imitationJusqua = os.clock() + math.random(18, 35)
	local autres = {}
	for _, q in ipairs(Players:GetPlayers()) do if q ~= cible then table.insert(autres, q) end end
	local imite = #autres > 0 and autres[math.random(#autres)] or nil
	local choix = {}
	for _, n in ipairs(C.IMITATIONS_PAR_PHASE[W.phase]) do
		if (n ~= "message" and n ~= "coups" and n ~= "pas") or imite then table.insert(choix, n) end
	end
	local quoi = choix[math.random(#choix)]
	if quoi == "voyants" and W.mode == "plafond" then
		racine:SetAttribute("Imitation", "voyants"); racine:SetAttribute("ImitationFin", os.clock() + 25)
	elseif quoi == "lampe" then
		racine:SetAttribute("Imitation", "lampe"); racine:SetAttribute("ImitationFin", os.clock() + 12)
	elseif quoi == "pas" and imite then
		evEffet:FireAllClients("pas", W.pos, imite.UserId, 4)
	elseif quoi == "coups" and imite then
		local rythme = imite:GetAttribute("RythmeFrappe") or "0.3,0.3,0.6"
		effet(cible, "coups", W.pos, rythme)
	elseif quoi == "message" and imite then
		local h = W.historiqueChat[imite.UserId]
		if h and #h > 0 then evMessage:FireClient(cible, imite.DisplayName, couleurNom(imite.Name):ToHex(), h[math.random(#h)]) end
	end
end

-- ================================================================ machine à états
local function plusSuspect()
	local best, bj = nil, 0
	for p, j in pairs(W.jauge) do if j > bj and p.Parent and hrp(p) then best, bj = p, j end end
	return best, bj
end
local function noeudAleatoireLoin(couche, distMin)
	for _ = 1, 30 do
		local i = math.random(Nav.n)
		if (not couche or Nav.couche[i] == couche) and (Nav:position(i) - W.pos).Magnitude > distMin and not Nav:estBloque(i) then return i end
	end
	return nil
end
local function versGaine()
	local g = Nav:plusProche(W.pos, 2, 200)
	if not (g and allerVers(Nav:position(g), 2)) then regler("rode") end         -- aucune grille praticable : elle reste au plafond
end

local derniereDecision = 0
local function decider()
	local p, j = plusSuspect()
	local maintenant = os.clock()
	if W.forcerFuite then
		W.forcerFuite = false
		if W.phase < 4 or W.pv < W.pvMax * 0.35 then
			task.spawn(function() W.occupe = true; coupEncre(); W.occupe = false end)
			regler("repli"); versGaine(); return
		end
	end
	if W.etat == "rode" then
		if p and j >= C.JAUGE.chasse and W.phase >= 2 then regler("chasse"); W.cible = p
		elseif p and j >= C.JAUGE.fouille then
			if W.phase >= 2 then regler("fouille"); W.chemin = nil
			else W.cible = p end                                -- phase 1 : elle observe et suit, sans attaquer
		end
		if p and W.phase == 1 and (hrp(p).Position - W.pos).Magnitude < C.PROCHE + 2 and pret("fouet") then
			W.occupe = true; task.spawn(function() coupFouet(p); regler("repli"); versGaine(); W.occupe = false end); return
		end
		if not W.chemin or W.forcerDeplacement then
			W.forcerDeplacement = false
			if W.cible and W.phase == 1 and hrp(W.cible) then
				local r = hrp(W.cible).Position; local dir = (W.pos - r); dir = Vector3.new(dir.X, 0, dir.Z)
				local garde = r + (dir.Magnitude > 0.1 and dir.Unit or Vector3.new(1, 0, 0)) * 22
				allerVers(garde, 1)
				if (r - W.pos).Magnitude < 40 then imiter(W.cible) end
			else
				local n = noeudAleatoireLoin(nil, 40); if n then allerVers(Nav:position(n)) end
			end
		end
	elseif W.etat == "fouille" then
		if p and j >= C.JAUGE.chasse then regler("chasse"); W.cible = p; return end
		if maintenant - W.etatDepuis > 20 then regler("rode"); W.chemin = nil; return end
		if not W.chemin then
			local but = W.dernierSignal and W.dernierSignal.pos
			-- les cachettes déjà utilisées près du signal passent en premier
			local best, bd = nil, 40
			for _, c in ipairs(W.cachettes) do
				local d = but and (c - but).Magnitude or (c - W.pos).Magnitude
				if d < bd then best, bd = c, d end
			end
			allerVers(best or but or W.pos, 1)
		end
		if p and W.phase >= 2 then imiter(p) end
	elseif W.etat == "chasse" then
		local cible = W.cible
		if not cible or not hrp(cible) or (humanoide(cible) and humanoide(cible).Health <= 0) then W.cible = p; cible = p end
		if not cible then regler("fouille"); return end
		local r = hrp(cible).Position
		local vu = W.dernierVu[cible] and (maintenant - W.dernierVu[cible]) < 8
		if not vu and (W.jauge[cible] or 0) < C.JAUGE.chasse * 0.6 then regler("fouille"); W.chemin = nil; return end
		local dist = (r - W.pos).Magnitude
		local horiz = Vector3.new(r.X - W.pos.X, 0, r.Z - W.pos.Z).Magnitude
		-- à portée : attaque
		if (W.mode == "sol" and dist <= C.COUPS.saisie.portee) or (W.mode == "plafond" and (horiz <= C.COUPS.chute.rayon or dist <= C.COUPS.fouet.portee)) then
			W.occupe = true; task.spawn(attaquer, cible); return
		end
		-- descendre au sol pour courir plus vite que le joueur
		if W.mode == "plafond" and W.phase >= 2 and dist < 45 and (maintenant - W.solFin) > C.SOL_REPOS_MIN and vu then
			task.spawn(descendre); return
		end
		if W.mode == "sol" then
			if maintenant - W.solDebut > C.SOL_DUREE_MAX then task.spawn(remonter); return end
			return                                               -- la course est gérée dans la boucle
		end
		if maintenant - derniereDecision > 0.5 or not W.chemin then allerVers(r, 1); derniereDecision = maintenant end
	elseif W.etat == "repli" then
		if not W.chemin then
			if W.mode == "gaine" then
				local n = noeudAleatoireLoin(2, 80); if n then allerVers(Nav:position(n), 2) end
				task.delay(math.random(6, 14), function()
					if W.etat == "repli" then regler("rode"); W.chemin = nil end
				end)
			else versGaine() end
		end
	end
end

-- ================================================================ boucle principale
local depart = Nav:plusProche(Vector3.new(0, 20, 0), 1, 400) or 1
W.pos = Nav:position(depart) + Vector3.new(0, 0.3, 0); W.noeud = depart
initialiserPV(); regler("rode"); racine:SetAttribute("Phase", 1); placer()
Players.PlayerAdded:Connect(function() if os.clock() - W.debut < 60 then initialiserPV() end end)

local accPerception, accDecision = 0, 0
RunService.Heartbeat:Connect(function(dt)
	if W.etat == "morte" or W.etat == "capturee" then return end
	accPerception += dt; accDecision += dt
	if accPerception >= 0.1 then percevoir(accPerception); accPerception = 0 end
	if accDecision >= 0.25 then
		accDecision = 0; majPhase()
		if W.brulure > os.clock() then bDegats:Fire(C.BRULURE_DPS * 0.25, "brulure") end
		if not W.occupe and W.etat ~= "etourdie" then decider() end
	end
	if W.occupe or W.etat == "etourdie" then return end
	if W.mode == "sol" and W.etat == "chasse" and W.cible and hrp(W.cible) then
		courirVers(hrp(W.cible).Position, dt)
	elseif W.mode == "sol" then
		task.spawn(remonter); W.occupe = true
	else
		suivreChemin(dt)
	end
	local fin = racine:GetAttribute("ImitationFin")
	if fin and os.clock() > fin then racine:SetAttribute("Imitation", nil); racine:SetAttribute("ImitationFin", nil) end
end)
