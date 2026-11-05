--[[ THE WITNESS — eau de la base (ModuleScript, ReplicatedStorage > Witness).
Retrouve la surface de l'eau sous (ou autour d')une position à partir des volumes tagués « Eau » de la map
(environ 30 cm partout, plus les salles inondées). Utilisé par les effets d'eau (EauEffets) et, si activé, par l'ouïe de la créature. ]]
local CollectionService = game:GetService("CollectionService")
local E = {}
local CELLULE = 32
local grille: { [string]: { BasePart } } = {}

local function cle(i: number, j: number): string return i .. ":" .. j end
local function ajouter(p: Instance)
	if not p:IsA("BasePart") then return end
	local s, c = p.Size, p.Position
	for i = math.floor((c.X - s.X / 2) / CELLULE), math.floor((c.X + s.X / 2) / CELLULE) do
		for j = math.floor((c.Z - s.Z / 2) / CELLULE), math.floor((c.Z + s.Z / 2) / CELLULE) do
			local k = cle(i, j); grille[k] = grille[k] or {}; table.insert(grille[k], p)
		end
	end
end
for _, p in ipairs(CollectionService:GetTagged("Eau")) do ajouter(p) end
CollectionService:GetInstanceAddedSignal("Eau"):Connect(ajouter)

--[[ hauteur de la surface de l'eau à la verticale de pos, si pos est dans l'eau ou juste au-dessus (jusqu'à « marge » studs) ;
nil sinon. Les volumes d'eau de la map sont alignés sur les axes. ]]
function E.surface(pos: Vector3, marge: number?): number?
	local l = grille[cle(math.floor(pos.X / CELLULE), math.floor(pos.Z / CELLULE))]
	if not l then return nil end
	local best: number? = nil
	for _, p in ipairs(l) do
		local s, c = p.Size, p.Position
		if math.abs(pos.X - c.X) <= s.X / 2 and math.abs(pos.Z - c.Z) <= s.Z / 2 then
			local haut, bas = c.Y + s.Y / 2, c.Y - s.Y / 2
			if pos.Y >= bas - 0.5 and pos.Y <= haut + (marge or 3) then
				if not best or haut > best then best = haut end
			end
		end
	end
	return best
end

-- vrai si les pieds d'un personnage sont dans l'eau ; renvoie aussi la surface
function E.pieds(perso: Model): (boolean, number?)
	local r = perso:FindFirstChild("HumanoidRootPart") :: BasePart?
	local h = perso:FindFirstChildOfClass("Humanoid")
	if not r or not h then return false, nil end
	local piedsY = r.Position.Y - h.HipHeight - r.Size.Y / 2
	local s = E.surface(Vector3.new(r.Position.X, piedsY, r.Position.Z), 1)
	return s ~= nil and s > piedsY + 0.05, s
end

return E
