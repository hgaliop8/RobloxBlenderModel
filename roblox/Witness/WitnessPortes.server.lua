--[[ THE WITNESS — frapper aux portes (Script, ServerScriptService).
Ajoute une action « Frapper » (touche E) sur chaque battant de porte (pièces taguées « Porte »). Le son part de la porte,
le bruit compte pour la créature, et le rythme de chaque joueur est retenu (attribut « RythmeFrappe ») : elle s'en sert
plus tard pour imiter un coéquipier. ]]
local RS = game:GetService("ReplicatedStorage")
local CollectionService = game:GetService("CollectionService")
local dossier = RS:WaitForChild("Witness")
local C = require(dossier:WaitForChild("WitnessConfig"))
local bBruit = dossier:WaitForChild("WitnessBruit")

local FENETRE = 2.5                 -- un rythme = les coups frappés en moins de 2,5 s
local enCours = {}                  -- joueur -> { t0, instants }

local function son(part)
	local id = C.SONS.coups; if not id or id == "" then return end
	local s = Instance.new("Sound"); s.SoundId = id; s.Volume = 1.2; s.RollOffMaxDistance = 60; s.Parent = part; s:Play()
	task.delay(3, function() s:Destroy() end)
end

local function equiper(porte)
	if not porte:IsA("BasePart") or porte:FindFirstChild("Frapper") then return end
	local pp = Instance.new("ProximityPrompt"); pp.Name = "Frapper"; pp.ActionText = "Frapper"; pp.ObjectText = "Porte"
	pp.KeyboardKeyCode = Enum.KeyCode.E; pp.HoldDuration = 0; pp.MaxActivationDistance = 7; pp.RequiresLineOfSight = false
	pp.Parent = porte
	pp.Triggered:Connect(function(joueur)
		son(porte); bBruit:Fire(porte.Position, 0.6)
		local e = enCours[joueur]; local t = os.clock()
		if not e or t - e.t0 > FENETRE then
			e = { t0 = t, instants = {} }; enCours[joueur] = e
			task.delay(FENETRE + 0.1, function()
				local f = enCours[joueur]; if f ~= e then return end
				enCours[joueur] = nil
				if #e.instants >= 2 then
					local d = {}
					for i = 2, #e.instants do table.insert(d, string.format("%.2f", e.instants[i] - e.instants[i - 1])) end
					joueur:SetAttribute("RythmeFrappe", table.concat(d, ","))
				end
			end)
		end
		table.insert(e.instants, t)
	end)
end

for _, p in ipairs(CollectionService:GetTagged("Porte")) do equiper(p) end
CollectionService:GetInstanceAddedSignal("Porte"):Connect(equiper)
