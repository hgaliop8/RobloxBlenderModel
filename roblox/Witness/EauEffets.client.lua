--[[ NADIR-4 — effets de l'eau (LocalScript, StarterPlayer > StarterPlayerScripts).
La base a environ 30 cm d'eau partout (volumes tagués « Eau »). Ce script ajoute, pour chaque joueur qui regarde :
  - des ronds dans l'eau et de petites éclaboussures sous les pas de tous les joueurs (plus forts en courant, à l'arrivée d'un saut) ;
  - le sillage de la créature quand elle nage au sol, les remous de ses bras qui touchent l'eau ;
  - une grosse gerbe quand elle tombe du plafond dans l'eau.
Aucun fichier à téléverser : les ronds sont dessinés par l'interface, les gouttes utilisent une texture intégrée à Roblox. ]]
local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local dossier = RS:WaitForChild("Witness")
local C = require(dossier:WaitForChild("WitnessConfig"))
local Eau = require(dossier:WaitForChild("WitnessEau"))
local racine = workspace:WaitForChild("WitnessRacine")

local fx = Instance.new("Folder"); fx.Name = "EauEffets"; fx.Parent = workspace
local LOIN = CFrame.new(0, -10000, 0)

-- ================================================================ ronds dans l'eau (réserve de pièces réutilisées)
type Rond = { part: Part, trait: UIStroke, t0: number, pos: Vector3, rayon: number, duree: number, force: number }
local reserve: { Rond } = {}
local actifs: { Rond } = {}
local function nouveauRond(): Rond
	local p = Instance.new("Part")
	p.Anchored = true; p.CanCollide = false; p.CanQuery = false; p.CanTouch = false; p.CastShadow = false
	p.Transparency = 1; p.Size = Vector3.new(1, 0.05, 1); p.CFrame = LOIN; p.Name = "Rond"
	local g = Instance.new("SurfaceGui"); g.Face = Enum.NormalId.Top; g.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
	g.PixelsPerStud = 40; g.LightInfluence = 1; g.Brightness = 1.6; g.Parent = p
	local f = Instance.new("Frame"); f.Size = UDim2.fromScale(1, 1); f.BackgroundTransparency = 1; f.Parent = g
	local coin = Instance.new("UICorner"); coin.CornerRadius = UDim.new(0.5, 0); coin.Parent = f
	local trait = Instance.new("UIStroke"); trait.Color = Color3.fromRGB(196, 226, 230); trait.Thickness = 4; trait.Transparency = 1; trait.Parent = f
	p.Parent = fx
	return { part = p, trait = trait, t0 = 0, pos = Vector3.zero, rayon = 1, duree = 1, force = 1 }
end
for _ = 1, 60 do table.insert(reserve, nouveauRond()) end

-- un rond qui s'élargit jusqu'à « rayon » en « duree » secondes et s'efface ; force 0..1 = netteté
local function rond(pos: Vector3, rayon: number, duree: number, force: number)
	local r = table.remove(reserve)
	if not r then
		if #actifs >= 160 then r = table.remove(actifs, 1) else r = nouveauRond() end
	end
	local rr = r :: Rond
	rr.t0 = os.clock(); rr.pos = pos; rr.rayon = rayon; rr.duree = duree; rr.force = force
	table.insert(actifs, rr)
end
local function majRonds()
	local t = os.clock()
	for i = #actifs, 1, -1 do
		local r = actifs[i]
		local a = (t - r.t0) / r.duree
		if a >= 1 then
			r.part.CFrame = LOIN; r.trait.Transparency = 1
			table.remove(actifs, i); table.insert(reserve, r)
		else
			local d = 0.4 + (r.rayon * 2 - 0.4) * (1 - (1 - a) * (1 - a))
			r.part.Size = Vector3.new(d, 0.05, d); r.part.CFrame = CFrame.new(r.pos)
			r.trait.Transparency = 1 - r.force * 0.85 * (1 - a) ^ 1.5
			r.trait.Thickness = 2 + 4 * (1 - a)
		end
	end
end

-- ================================================================ gouttes
local socle = Instance.new("Part"); socle.Anchored = true; socle.CanCollide = false; socle.CanQuery = false; socle.CanTouch = false
socle.Transparency = 1; socle.Size = Vector3.one; socle.CFrame = CFrame.new(); socle.Name = "Gouttes"; socle.Parent = fx
local point = Instance.new("Attachment"); point.Parent = socle
local function emetteur(vMin: number, vMax: number, angle: number, taille: number): ParticleEmitter
	local pe = Instance.new("ParticleEmitter")
	pe.Texture = "rbxasset://textures/particles/smoke_main.dds"
	pe.Enabled = false; pe.Rate = 0
	pe.Lifetime = NumberRange.new(0.35, 0.75); pe.Speed = NumberRange.new(vMin, vMax)
	pe.EmissionDirection = Enum.NormalId.Top; pe.SpreadAngle = Vector2.new(angle, angle)
	pe.Acceleration = Vector3.new(0, -90, 0); pe.Drag = 0.6
	pe.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, taille), NumberSequenceKeypoint.new(1, taille * 0.4) })
	pe.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(1, 1) })
	pe.Color = ColorSequence.new(Color3.fromRGB(205, 228, 232)); pe.LightInfluence = 1; pe.LightEmission = 0.15
	pe.Parent = point
	return pe
end
local gouttes = emetteur(5, 12, 28, 0.22)
local gerbe = emetteur(14, 28, 42, 0.38)
local function eclabousser(pe: ParticleEmitter, pos: Vector3, n: number)
	point.WorldPosition = pos; pe:Emit(n)
end

local function son(pos: Vector3, nom: string, volume: number)
	local id = C.SONS[nom]; if not id or id == "" then return end
	local a = Instance.new("Attachment"); a.WorldPosition = pos; a.Parent = workspace.Terrain
	local s = Instance.new("Sound"); s.SoundId = id; s.Volume = volume; s.RollOffMaxDistance = 60
	s.PlaybackSpeed = 0.9 + math.random() * 0.25; s.Parent = a; s:Play()
	task.delay(4, function() a:Destroy() end)
end

-- ================================================================ joueurs : pas dans l'eau
type EtatPas = { prochain: number, cote: number, calme: number, dedans: boolean }
local pas: { [Model]: EtatPas } = setmetatable({}, { __mode = "k" }) :: any
local function joueurs(t: number)
	for _, pl in ipairs(Players:GetPlayers()) do
		local ch = pl.Character
		local r = ch and ch:FindFirstChild("HumanoidRootPart") :: BasePart?
		if ch and r then
			local dedans, surf = Eau.pieds(ch)
			local e = pas[ch]; if not e then e = { prochain = 0, cote = 1, calme = t, dedans = false }; pas[ch] = e end
			local vel = r.AssemblyLinearVelocity
			if dedans and surf then
				local p = Vector3.new(r.Position.X, surf + 0.03, r.Position.Z)
				if not e.dedans and vel.Y < -12 then                       -- arrivée d'un saut ou d'une chute
					rond(p, 3.2, 1.5, 1); eclabousser(gouttes, p, 24); son(p, "eclabousse", 1)
				end
				local v = Vector3.new(vel.X, 0, vel.Z).Magnitude
				local allure = C.allure(pl, v)
				if allure then
					if t >= e.prochain then
						-- sprint : grosses éclaboussures et bruit fort ; marche : clapotis ; accroupi : rides silencieuses
						local course, accroupi = allure == "course", allure == "accroupi"
						e.prochain = t + (course and 0.28 or (accroupi and 0.6 or 0.42)); e.cote = -e.cote
						local lat = r.CFrame.RightVector * (0.5 * e.cote)
						local q = p + Vector3.new(lat.X, 0, lat.Z)
						rond(q, course and 2.8 or (accroupi and 1.1 or 1.8), course and 1.1 or 1.4, course and 1 or (accroupi and 0.3 or 0.6))
						if course then eclabousser(gouttes, q, 12); son(q, "eclabousse", 1)
						elseif not accroupi then eclabousser(gouttes, q, 2); son(q, "eclabousse", 0.35) end
					end
					e.calme = t
				elseif t - e.calme > 2.5 then                                -- immobile : un léger rond de temps en temps
					e.calme = t; rond(p, 1.2, 1.8, 0.3)
				end
			end
			e.dedans = dedans
		end
	end
end

-- ================================================================ la créature : sillage, bras qui touchent l'eau, gerbe à l'atterrissage
local precedent = racine.Position; local vitesse = 0
local prochainSillage, prochainRemous = 0, 0
local derniereGerbe = 0
local pointesY: { [number]: number } = {}
local dejaVu: { [string]: number } = {}
local function creature(t: number, dt: number)
	local p = racine.Position
	local d = Vector3.new(p.X - precedent.X, 0, p.Z - precedent.Z)
	vitesse += (d.Magnitude / math.max(dt, 1e-3) - vitesse) * math.min(1, dt * 8)
	precedent = p
	local mode = racine:GetAttribute("Mode")
	-- gerbe : au moment exact de l'impact d'une chute
	local coupT = racine:GetAttribute("CoupT") or 0
	if racine:GetAttribute("Coup") == "descente" and coupT ~= derniereGerbe then
		local e = workspace:GetServerTimeNow() - coupT
		local impact = (racine:GetAttribute("ChuteDecroche") or C.DECROCHAGE) + (racine:GetAttribute("ChuteTf") or 0.35)
		local sol = racine:GetAttribute("ChuteSol")
		if e >= impact and typeof(sol) == "Vector3" then
			derniereGerbe = coupT
			local s = Eau.surface(sol, 3)
			if s then
				local q = Vector3.new(sol.X, s + 0.03, sol.Z)
				eclabousser(gerbe, q, 70); eclabousser(gouttes, q, 30)
				rond(q, 5.5, 1.6, 1); rond(q, 3.5, 1.2, 0.9)
				task.delay(0.18, function() rond(q, 7.5, 2.0, 0.7) end)
				son(q, "eclabousse", 2)
			end
		end
	end
	-- attaques au sol : grand cercle du balayage, éclaboussure du fouet sur sa cible
	local coup = racine:GetAttribute("Coup")
	if mode == "sol" and (coup == "balayage" or coup == "fouet") and dejaVu[coup] ~= coupT then
		local info = C.COUPS[coup]
		local retard = (coup == "fouet") and 0.28 or 0                    -- le bout du fouet arrive après le signe
		if workspace:GetServerTimeNow() - coupT >= (info and info.signe or 0.5) + retard then
			dejaVu[coup] = coupT
			local s0 = Eau.surface(p, 2)
			if s0 then
				local q = Vector3.new(p.X, s0 + 0.03, p.Z)
				if coup == "balayage" then
					rond(q, 9, 1.3, 1); rond(q, 6, 1.0, 0.8)
					for i = 0, 7 do
						local a = i * math.pi / 4
						eclabousser(gouttes, q + Vector3.new(math.cos(a) * 5, 0, math.sin(a) * 5), 6)
					end
					son(q, "eclabousse", 1.5)
				else
					local id = racine:GetAttribute("Cible")
					local pl = id and Players:GetPlayerByUserId(id)
					local r = pl and pl.Character and pl.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
					if r then
						local m = Vector3.new(r.Position.X, s0 + 0.03, r.Position.Z)
						rond(m, 2.2, 1.0, 0.8); eclabousser(gouttes, m, 8)
					end
				end
			end
		end
	end
	if mode ~= "sol" then table.clear(pointesY); return end
	local s = Eau.surface(p, 2)
	if not s then return end
	local avant = d.Magnitude > 1e-3 and d.Unit or Vector3.new(0, 0, -1)
	-- sillage : une suite de ronds le long de son passage forme le V derrière elle
	if vitesse > 3 and t >= prochainSillage then
		prochainSillage = t + (vitesse > 16 and 0.06 or 0.12)
		local q = Vector3.new(p.X, s + 0.03, p.Z)
		rond(q, 2.2 + vitesse * 0.08, 1.4, math.min(1, 0.4 + vitesse / 30))
		if vitesse > 16 then eclabousser(gouttes, q + avant * 2, 4) end
		if t >= prochainRemous then prochainRemous = t + 0.6; son(q, "remous", math.min(1, vitesse / 26)) end
	end
	-- pointes des bras qui retouchent l'eau en marchant
	local corps = workspace:FindFirstChild("WitnessCorps")
	if corps then
		for k = 0, 7 do
			local b = corps:FindFirstChild(("Bras%d_8"):format(k), true)
			if b and b:IsA("Bone") then
				local y = b.TransformedWorldCFrame.Position.Y
				local avantY = pointesY[k]
				if avantY and avantY > s + 0.1 and y <= s then
					local q = b.TransformedWorldCFrame.Position
					q = Vector3.new(q.X, s + 0.03, q.Z)
					rond(q, 1.1, 1.0, 0.6); eclabousser(gouttes, q, 2)
				end
				pointesY[k] = y
			end
		end
	end
end

RunService.RenderStepped:Connect(function(dt)
	local t = os.clock()
	joueurs(t)
	creature(t, dt)
	majRonds()
end)
