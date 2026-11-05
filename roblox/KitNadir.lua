--[[ NADIR-4 : préparation et placement du kit 3D et de l'architecture maillée.
À coller dans la barre de commande de Roblox Studio (Affichage > Barre de commande), APRÈS avoir importé :
  1. matieres.glb   -> renommer le modèle importé « Matieres » et le ranger dans ServerStorage
  2. kit_1.glb, kit_2.glb et kit_3.glb -> les ranger dans ServerStorage > KitNadir
  3. archi_*.glb (un par secteur) -> les laisser dans Workspace, où l'import les a mis (le script les recale tout seul)
Le script :
  a) habille chaque MeshPart du kit d'après son nom (texture PBR teintée, verre, liquide, matière unie / néon) ;
  b) remplace chaque emplacement « Kit:<objet> » de la map (petites boîtes invisibles) par une copie du modèle correspondant.
On peut le relancer sans risque : les modèles déjà habillés sont ignorés, les emplacements déjà remplis aussi. ]]

local SS = game:GetService("ServerStorage")
local mats = SS:FindFirstChild("Matieres")
local kit = SS:FindFirstChild("KitNadir")
assert(mats, "Modèle 'Matieres' introuvable dans ServerStorage")
assert(kit, "Dossier 'KitNadir' introuvable dans ServerStorage")

-- matière physique Roblox (sons de pas, physique) d'après la texture
local PHYS = { metal_peint = Enum.Material.Metal, metal_brut = Enum.Material.Metal, metal_rouille = Enum.Material.CorrodedMetal,
	tole_striee = Enum.Material.DiamondPlate, beton = Enum.Material.Concrete, vinyle = Enum.Material.SmoothPlastic,
	carrelage = Enum.Material.Marble, moquette = Enum.Material.Fabric, tissu = Enum.Material.Fabric, matelas = Enum.Material.Fabric,
	bois = Enum.Material.Wood, plastique = Enum.Material.Plastic, peinture_mur = Enum.Material.SmoothPlastic,
	plafond = Enum.Material.SmoothPlastic, caoutchouc = Enum.Material.Rubber, simili_cuir = Enum.Material.Leather,
	carton = Enum.Material.Cardboard, grille_vent = Enum.Material.Metal }

local function surface(tex)
	local src = mats:FindFirstChild(tex, true)
	if not src then return nil end
	return src:FindFirstChildOfClass("SurfaceAppearance")
end

local function habiller(p)
	if not p:IsA("MeshPart") or p:GetAttribute("Habille") then return end
	local n = p.Name:gsub("%.%d+$", "")
	local kind, rest = n:match("^(%a)_(.+)$")
	if kind == "T" then
		local tex, hex = rest:match("^(.+)_(%x%x%x%x%x%x)$")
		local sa = tex and surface(tex)
		if sa then
			for _, c in ipairs(p:GetChildren()) do if c:IsA("SurfaceAppearance") then c:Destroy() end end
			local s = sa:Clone(); s.Color = Color3.fromHex(hex); s.Parent = p
		end
		p.Color = Color3.fromHex(hex or "C8C8C8"); p.Material = PHYS[tex] or Enum.Material.SmoothPlastic
	elseif kind == "V" then
		p.Material = Enum.Material.Glass; p.Transparency = 0.65; p.Color = Color3.fromHex(rest); p.CastShadow = false
	elseif kind == "L" then
		p.Material = Enum.Material.Glass; p.Transparency = 0.35; p.Color = Color3.fromHex(rest); p.CastShadow = false
	elseif kind == "P" then
		local hex, r, m, e = rest:match("^(%x%x%x%x%x%x)_(%d+)_(%d+)_(%d+)$")
		p.Color = Color3.fromHex(hex or "C8C8C8")
		if e and tonumber(e) > 0 then p.Material = Enum.Material.Neon
		elseif m and tonumber(m) >= 50 then p.Material = Enum.Material.Metal; p.Reflectance = (r and tonumber(r) < 20) and 0.25 or 0.05
		else p.Material = (r and tonumber(r) < 25) and Enum.Material.SmoothPlastic or Enum.Material.Plastic end
	elseif n == "Origine" then
		return
	end
	p.Anchored = true
	-- collisions : les petits éléments ne bloquent pas, le reste en boîte englobante
	local s = p.Size
	if s.X * s.Y * s.Z < 0.4 or math.min(s.X, s.Y, s.Z) < 0.08 and math.max(s.X, s.Y, s.Z) < 2 then
		p.CanCollide = false; p.CanTouch = false; p.CanQuery = true
	else
		p.CollisionFidelity = Enum.CollisionFidelity.Box
	end
	p:SetAttribute("Habille", true)
end

-- a) recensement des objets du kit (à n'importe quelle profondeur : un objet = un modèle qui contient un repère « Origine »),
--    habillage et pivot sur le repère
local KITS, nbm = {}, 0
for _, o in ipairs(kit:GetDescendants()) do
	if o:IsA("BasePart") and o.Name:gsub("%.%d+$", "") == "Origine" and o.Parent then
		local m = o.Parent
		if not m:IsA("Model") then                     -- au cas où l'import aurait créé un dossier
			local mm = Instance.new("Model"); mm.Name = m.Name
			for _, c in ipairs(m:GetChildren()) do c.Parent = mm end
			mm.Parent = m.Parent; m:Destroy(); m = mm
		end
		m.WorldPivot = CFrame.new(o.Position)
		o:Destroy()
		m.Name = m.Name:gsub("%.%d+$", "")
		m:SetAttribute("KitOk", true)
	end
end
for _, m in ipairs(kit:GetDescendants()) do
	if m:IsA("Model") and m:GetAttribute("KitOk") then
		for _, p in ipairs(m:GetDescendants()) do habiller(p) end
		KITS[m.Name] = m; nbm += 1
	end
end
print(("NADIR-4 : %d modèles du kit prêts"):format(nbm))

-- b) placement
local places, manquants = 0, {}
for _, e in ipairs(workspace:GetDescendants()) do
	if e:IsA("BasePart") and e.Name:sub(1, 4) == "Kit:" and not e:GetAttribute("Rempli") then
		local nom = e.Name:sub(5)
		local src = KITS[nom]
		if src then
			local c = src:Clone()
			c:PivotTo(e.CFrame)
			c.Name = nom
			local dossier = e.Parent
			if dossier and dossier.Name:sub(1, 6) == "Objet_" then      -- supprime la version en blocs
				for _, x in ipairs(dossier:GetChildren()) do if x ~= e then x:Destroy() end end
			end
			c.Parent = dossier
			e:SetAttribute("Rempli", true)
			e.Transparency = 1; e.CanCollide = false; e.CanQuery = false
			places += 1
		else
			manquants[nom] = (manquants[nom] or 0) + 1
		end
	end
end
print(("NADIR-4 : %d objets placés"):format(places))
for nom, k in pairs(manquants) do warn(("  modèle manquant : %s (%d emplacements)"):format(nom, k)) end

-- c) architecture maillée : recalage en coordonnées réelles (repère « Origine » = point 0,0,0 de la map) et habillage
local dossierArchi = workspace:FindFirstChild("Nadir4_Architecture") or Instance.new("Folder")
dossierArchi.Name = "Nadir4_Architecture"; dossierArchi.Parent = workspace
local nba = 0
for _, m in ipairs(workspace:GetChildren()) do
	if m:IsA("Model") and m.Name:sub(1, 6) == "archi_" then
		local o = m:FindFirstChild("Origine", true)
		if o then m.WorldPivot = CFrame.new(o.Position); o:Destroy(); m:PivotTo(CFrame.new()) end
		for _, p in ipairs(m:GetDescendants()) do
			if p:IsA("MeshPart") then
				habiller(p)
				p.CanCollide = false; p.CanTouch = false; p.CanQuery = false     -- les collisions sont assurées par les volumes invisibles du .rbxlx
			end
		end
		m.Parent = dossierArchi; nba += 1
	end
end
print(("NADIR-4 : %d secteurs d'architecture recalés et habillés"):format(nba))
