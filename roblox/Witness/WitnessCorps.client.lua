--[[ THE WITNESS — corps (LocalScript, StarterPlayer > StarterPlayerScripts).
Chaque joueur affiche sa propre copie du modèle et l'anime os par os à partir de la pièce « WitnessRacine » déplacée par le serveur :
ondulation et marche des bras, respiration du manteau, regard qui suit le joueur, gestes d'attaque, lumières et imitations.
Gère aussi les effets reçus du serveur (recul, chute, saisie, encre, coups à la porte, faux pas, faux messages, élimination).
Modèle attendu : ReplicatedStorage > Witness > WitnessModele (import de witness.glb, squelette inclus). ]]

local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Lighting = game:GetService("Lighting")
local UserInputService = game:GetService("UserInputService")
local TextChatService = game:GetService("TextChatService")

local joueur = Players.LocalPlayer
local dossier = RS:WaitForChild("Witness")
local C = require(dossier:WaitForChild("WitnessConfig"))
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

-- halo et lampe d'imitation
local ancre = Instance.new("Attachment"); ancre.Parent = osRacine or corps.PrimaryPart or pieces[1]
local halo = Instance.new("PointLight"); halo.Color = Color3.fromRGB(86, 224, 208); halo.Range = 10; halo.Brightness = 0.6; halo.Shadows = false; halo.Parent = ancre
local fausseLampe = Instance.new("SpotLight"); fausseLampe.Color = Color3.fromRGB(255, 236, 205); fausseLampe.Angle = 38; fausseLampe.Range = 45
fausseLampe.Brightness = 0; fausseLampe.Face = Enum.NormalId.Right; fausseLampe.Shadows = true; fausseLampe.Parent = ancre

-- ================================================================ animation des os
local ROT = CFrame.Angles(0, math.pi / 2, 0)            -- le devant du modèle (+X) suit le LookVector de la racine
local cfAffiche = racine.CFrame * ROT
local precedent = racine.Position; local vitesse = 0
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

local function animer(t, dt)
	local mode = racine:GetAttribute("Mode") or "plafond"
	local coup = racine:GetAttribute("Coup"); local coupT = racine:GetAttribute("CoupT") or 0
	local e = workspace:GetServerTimeNow() - coupT; local signe = coup and C.COUPS[coup] and C.COUPS[coup].signe or 0.5
	local saisie = racine:GetAttribute("Saisie") ~= nil
	local etat = racine:GetAttribute("Etat")
	local v = vitesse
	local marche = math.clamp(v / 10, 0, 1)
	local wg = 2 + v * 0.8
	for k = 0, 7 do
		local ph = phases[k]
		for j = 1, 8 do
			local b = os_[("Bras%d_%d"):format(k, j)]
			-- ondulation de repos : vague qui descend le bras
			local yaw = 0.13 * math.sin(t * 1.3 - j * 0.55 + ph)
			local pitch = 0.04 * math.sin(t * 0.9 + j * 0.6 + ph)
			if j >= 7 then pitch += 0.22 + 0.08 * math.sin(t * 1.7 + ph) end          -- pointes qui s'enroulent
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
			if coup == "fouet" and (k == 0 or k == 7) then
				if e < signe then pitch += lisse(e / signe) * 0.4 * (j / 8) * 2       -- le bras s'enroule en spirale
				elseif e < signe + 0.3 then pitch -= 0.35; yaw += (k == 0 and 0.4 or -0.4) * (j <= 3 and 1 or 0.4)
				end
			elseif coup == "balayage" then
				if e < signe then pitch -= 0.08 * lisse(e / signe) else yaw += 0.6 * math.sin(math.clamp((e - signe) / 0.35, 0, 1) * math.pi) end
			elseif (coup == "saisie" or coup == "enlevement" or saisie) and (k == 0 or k == 7 or k == 1 or k == 6) then
				local a = lisse(e / signe)
				pitch += a * (j == 1 and 0.6 or (j <= 4 and 0.25 or 0.45))
				yaw += a * (k <= 1 and 0.2 or -0.2)
			elseif coup == "chute" then
				pitch += 0.12 + 0.03 * math.sin(t * 22 + k)                        -- tension, tremblement
			elseif coup == "descente" then
				pitch += lisse(e / 0.6) * (j >= 4 and 0.35 or 0.1)
			elseif coup == "encre" and j <= 3 then
				pitch -= 0.15 * math.sin(math.clamp(e / 0.8, 0, 1) * math.pi)
			end
			ang(b, pitch, yaw)
		end
	end
	-- manteau qui respire, tête, bec
	local respi = math.sin(t * 1.25)
	local contraction = (coup == "encre") and math.sin(math.clamp(e / 0.6, 0, 1) * math.pi) * 0.25 or 0
	ang(os_.Manteau1, 0.05 * respi + contraction, 0.02 * math.sin(t * 0.7))
	ang(os_.Manteau2, 0.08 * math.sin(t * 1.25 + 0.5) + contraction, 0.04 * math.sin(t * 0.6))
	local morsure = (coup == "morsure") and math.sin(math.clamp(e / (signe + 0.2), 0, 1) * math.pi) or 0
	ang(os_.Tete, -0.3 * morsure + 0.03 * math.sin(t * 0.8), 0)
	ang(os_.Bec, 0.5 * morsure, 0)
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
	local cible = racine.CFrame * ROT
	cfAffiche = cfAffiche:Lerp(cible, 1 - math.exp(-14 * dt))
	corps:PivotTo(cfAffiche)
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
		debat = UserInputService.InputBegan:Connect(function(io, traite)
			if not traite and (io.KeyCode == Enum.KeyCode.Space or io.KeyCode == Enum.KeyCode.ButtonA) then evDebat:FireServer() end
		end)
	elseif quoi == "relache" then
		aide.Text = ""; if debat then debat:Disconnect(); debat = nil end
	elseif quoi == "elimine" then
		aide.Text = ""; if debat then debat:Disconnect(); debat = nil end
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
