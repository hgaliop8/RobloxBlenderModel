--[[ THE WITNESS — navigation (ModuleScript, ReplicatedStorage > Witness).
Charge le réseau généré (NavWitness) : plafonds, gaines, portes, grilles ; plus court chemin A* ; recherche du nœud le plus proche. ]]
local Nav = {}
Nav.__index = Nav

local PLAFOND, GAINE = 1, 2
Nav.TYPES = { [1] = "plafond", [2] = "gaine", [3] = "porte", [4] = "ouverture", [5] = "grille", [6] = "puits" }
local CELLULE = 16

local function cle(x, y, z) return math.floor(x / CELLULE) .. ":" .. math.floor(y / CELLULE) .. ":" .. math.floor(z / CELLULE) end

function Nav.new(N)
	local self = setmetatable({}, Nav)
	self.pos, self.couche, self.esp = {}, {}, {}
	self.adj = {}          -- adj[i] = { {j, type, passage}, ... }
	self.grilleCellules = {}
	self.parEspace = {}
	self.espaces = N.espaces
	self.boites = N.boites
	local n = #N.noeuds // 5
	for i = 1, n do
		local b = (i - 1) * 5
		local p = Vector3.new(N.noeuds[b + 1], N.noeuds[b + 2], N.noeuds[b + 3])
		self.pos[i] = p; self.couche[i] = N.noeuds[b + 4]; self.esp[i] = N.espaces[N.noeuds[b + 5]]
		self.adj[i] = {}
		local k = cle(p.X, p.Y, p.Z)
		local c = self.grilleCellules[k]; if not c then c = {}; self.grilleCellules[k] = c end
		table.insert(c, i)
		local e = self.esp[i]; self.parEspace[e] = self.parEspace[e] or {}; table.insert(self.parEspace[e], i)
	end
	self.n = n
	for k = 1, #N.aretes // 3 do
		local b = (k - 1) * 3
		local a, c, t = N.aretes[b + 1], N.aretes[b + 2], N.aretes[b + 3]
		local pas = N.passages[k]
		local pp = pas and Vector3.new(pas.x, pas.y, pas.z) or nil
		local typePorte = pas and pas.t or nil
		table.insert(self.adj[a], { c, t, pp, typePorte })
		table.insert(self.adj[c], { a, t, pp, typePorte })
	end
	self.grilles = N.grilles
	self.bloque = {}       -- bloque[i] = instant jusqu'auquel le nœud est interdit (feu)
	return self
end

function Nav:position(i) return self.pos[i] end
function Nav:espace(i) return self.esp[i] end
function Nav:estGaine(i) return self.couche[i] == GAINE end
function Nav:noeudsEspace(nom) return self.parEspace[nom] or {} end

-- espace (salle ou couloir) qui contient la position, d'après les boîtes du plan
function Nav:espaceEn(p)
	local best, aire = nil, math.huge
	for i, b in ipairs(self.boites) do
		if b[1] ~= b[3] and p.X >= b[1] - 0.5 and p.X <= b[3] + 0.5 and p.Z >= b[2] - 0.5 and p.Z <= b[4] + 0.5 and p.Y >= b[5] - 3 and p.Y <= b[6] + 3 then
			local a = (b[3] - b[1]) * (b[4] - b[2])
			if a < aire then best, aire = self.espaces[i], a end
		end
	end
	return best
end

-- nœud le plus proche (couche facultative : 1 plafond, 2 gaine)
function Nav:plusProche(p, couche, rayonMax)
	rayonMax = rayonMax or 64
	local best, bd = nil, math.huge
	local r = math.ceil(rayonMax / CELLULE)
	local cx, cy, cz = math.floor(p.X / CELLULE), math.floor(p.Y / CELLULE), math.floor(p.Z / CELLULE)
	for dx = -r, r do for dy = -2, 2 do for dz = -r, r do
		local c = self.grilleCellules[(cx + dx) .. ":" .. (cy + dy) .. ":" .. (cz + dz)]
		if c then
			for _, i in ipairs(c) do
				if not couche or self.couche[i] == couche then
					local d = (self.pos[i] - p).Magnitude
					if d < bd then best, bd = i, d end
				end
			end
		end
	end end end
	return best, bd
end

function Nav:bloquer(i, jusqua) self.bloque[i] = jusqua end
function Nav:estBloque(i) local t = self.bloque[i]; return t ~= nil and t > os.clock() end

-- file de priorité (tas binaire)
local function tasPush(h, prio, v)
	table.insert(h, { prio, v }); local i = #h
	while i > 1 do
		local p = i // 2
		if h[p][1] <= h[i][1] then break end
		h[p], h[i] = h[i], h[p]; i = p
	end
end
local function tasPop(h)
	local top = h[1]; local last = table.remove(h)
	if #h > 0 then
		h[1] = last; local i = 1
		while true do
			local l, r, m = i * 2, i * 2 + 1, i
			if l <= #h and h[l][1] < h[m][1] then m = l end
			if r <= #h and h[r][1] < h[m][1] then m = r end
			if m == i then break end
			h[m], h[i] = h[i], h[m]; i = m
		end
	end
	return top
end

--[[ plus court chemin de a à b.
opts.portesFermees(typePorte, passage) -> true si la porte est infranchissable ; opts.cout(i, j, type) -> surcoût ;
renvoie une liste d'étapes { noeud, pos, type (de l'arête qui y mène), passage } ]]
function Nav:chemin(a, b, opts)
	opts = opts or {}
	if not a or not b then return nil end
	local g, venu, arete = { [a] = 0 }, {}, {}
	local h = {}; tasPush(h, 0, a)
	local cible = self.pos[b]
	local ferme = {}
	local iter = 0
	while #h > 0 do
		iter += 1; if iter > 40000 then break end
		local cur = tasPop(h)[2]
		if cur == b then break end
		if not ferme[cur] then
			ferme[cur] = true
			for _, e in ipairs(self.adj[cur]) do
				local j, t, pp, tp = e[1], e[2], e[3], e[4]
				if not ferme[j] and not self:estBloque(j) and not (t == 3 and opts.portesFermees and opts.portesFermees(tp, pp)) then
					local d = (self.pos[j] - self.pos[cur]).Magnitude
					local vit = self.couche[j] == GAINE and 26 or 14
					local c = g[cur] + d / vit + (t == 5 and 1.2 or 0) + (t == 3 and 0.8 or 0) + (opts.cout and opts.cout(cur, j, t) or 0)
					if g[j] == nil or c < g[j] then
						g[j] = c; venu[j] = cur; arete[j] = e
						tasPush(h, c + (self.pos[j] - cible).Magnitude / 26, j)
					end
				end
			end
		end
	end
	if venu[b] == nil and a ~= b then return nil end
	local etapes = {}
	local cur = b
	while cur ~= a do
		local e = arete[cur]
		table.insert(etapes, 1, { noeud = cur, pos = self.pos[cur], type = Nav.TYPES[e[2]], passage = e[3], porte = e[4] })
		cur = venu[cur]
	end
	table.insert(etapes, 1, { noeud = a, pos = self.pos[a], type = "depart" })
	return etapes
end

return Nav
