--[[ THE WITNESS — réglages (ModuleScript, à placer dans ReplicatedStorage > Witness).
Toutes les valeurs du document « The Witness — Comportement et déplacements ». Unités : studs, secondes, PV. ]]
local C = {}

-- joueur (référence)
C.JOUEUR_MARCHE, C.JOUEUR_COURSE = 12, 20
C.JOUEUR_PV = 100

-- déplacements (studs/s)
C.VITESSE = { plafond = 14, plafond_pointe = 18, gaine = 26, mur = 12, sol = 26, nage = 32 }
C.SOL_DUREE_MAX = 6          -- course au sol d'affilée
C.SOL_REPOS_MIN = 8          -- temps minimal en hauteur avant une nouvelle course
C.VIRAGE_LENT = 18           -- vitesse pendant 0,5 s après un virage serré au sol
C.GRILLE_PASSAGE = 1.2       -- entrer / sortir d'une grille
C.MONTEE_DUREE = 1.5         -- sol -> plafond par le mur
-- se laisser tomber du plafond : décrochage (l'avant pend, les bras arrière tiennent), chute libre (gravité du jeu), atterrissage
C.DECROCHAGE = 0.3           -- descente volontaire
C.DECROCHAGE_EMBUSCADE = 0.12 -- chute dévorante sur un joueur : presque sans prévenir
C.ATTERRISSAGE = 0.45        -- impact, corps écrasé, bras qui s'étalent puis se reprennent
C.SAISIE_DEVANT, C.SAISIE_HAUTEUR = 2.1, 3.6   -- position du joueur étranglé (centre du torse) par rapport à elle : devant, au-dessus du sol

-- perception
C.PROCHE = 6                 -- en dessous : repéré même immobile dans le noir
C.VISION_ANGLE = 160         -- champ de vision total (degrés)
C.JAUGE = {
	proche = 100,            -- par seconde (100 en 1 s)
	lampe_vue = 60, lampe_braquee = 100, lampe_portee = 90,
	lumiere_bouge = 25, lumiere_portee = 50,
	noir_marche = 10, noir_marche_portee = 20,
	noir_immobile = 8, noir_immobile_portee = 12,
	course = 30, course_portee = 30,
	bruit = 40, bruit_portee = 40,
	chat = 15, chat_portee = 25,
	seul_mult = 1.5, seul_rayon = 30,
	baisse = 5,
	fouille = 40, chasse = 100,
}
-- eau (environ 30 cm partout dans la base) : réglages de gameplay, désactivés par défaut
-- eau (environ 30 cm partout dans la base) : le bruit dépend de l'allure ; l'eau ne ralentit pas les joueurs
C.EAU = {
	course = { portee = 45, bruit = 45 },   -- sprint dans l'eau : entendu de loin, à travers les murs (s'ajoute au bruit de course)
	marche = { portee = 15, bruit = 10 },   -- marche normale : léger clapotis, entendu de près
	-- accroupi : aucun bruit. Le script d'accroupissement du jeu met l'attribut « Accroupi » = true sur le personnage
	-- (ou sur le joueur) ; à défaut, une vitesse au plus égale à vitesse_accroupi compte comme accroupi.
	vitesse_accroupi = 7,
	vitesse_course = 15,                    -- au-dessus : sprint
}
-- allure d'un joueur dans l'eau : "course", "marche", "accroupi" ou nil (immobile)
function C.allure(joueur: Player, vitesse: number): string?
	local ch = joueur.Character
	if (ch and ch:GetAttribute("Accroupi")) or joueur:GetAttribute("Accroupi") then return vitesse > 1 and "accroupi" or nil end
	if vitesse <= 1.5 then return nil end
	if vitesse > C.EAU.vitesse_course then return "course" end
	if vitesse <= C.EAU.vitesse_accroupi then return "accroupi" end
	return "marche"
end
C.FIXEE_DUREE = 2            -- un joueur qui fixe ses lumières plus longtemps la fait partir

-- phases (secondes depuis le début, preuves ramassées)
C.PHASES = {
	{ nom = "Le regard" },
	{ nom = "La fouille", temps = 6*60, preuves = 2 },
	{ nom = "La traque", temps = 14*60, preuves = 4, premier_mort = true },
	{ nom = "La rage", pv_perdus = 0.5, implosion = true },
}

-- attaques : portée, dégâts, signe (s), recharge (s), phase minimale
C.COUPS = {
	fouet     = { portee = 10, degats = 25, recul = 4, signe = 0.5, recharge = 4, phase = 1 },
	balayage  = { portee = 9, degats = 15, renverse = 1.5, signe = 0.6, recharge = 10, phase = 2 },
	morsure   = { portee = 4, degats = 40, signe = 0.35, recharge = 6, phase = 2 },
	saisie    = { portee = 8, dps = 12, duree_min = 5, duree_max = 8, liberation = 150, signe = 0.7, recharge = 20, phase = 2 },
	enlevement= { portee_grille = 12, portee = 8, trainee = 3, liberation = 100, signe = 1.0, recharge = 0, phase = 3 },
	chute     = { rayon = 3, signe = 1.5, recharge = 0, phase = 2 },
	encre     = { rayon = 12, duree = 4, signe = 0.5, recharge = 30, phase = 1 },
}
C.REPLI_APRES_ELIMINATION = 0.7   -- probabilité de filer dans les gaines après une élimination (phases 1 à 3)

-- points de vie, feu
C.PV_BASE, C.PV_PAR_JOUEUR = 2000, 400
C.MULT_ORDINAIRE, C.MULT_FEU = 0.4, 2.5
C.BRULURE_DPS, C.BRULURE_DUREE = 15, 3
C.ETOURDI_SEUIL, C.ETOURDI_FENETRE, C.ETOURDI_DUREE = 0.15, 4, 6
C.PALIERS_FUITE = { 0.75, 0.5, 0.35 }
C.CAPTURE_PV, C.CAPTURE_FENETRE = 0.25, 6
C.PEUR_FEU = 15                   -- recule devant un feu plus proche (sauf phase 4)
C.FEU_INTERDIT = 60               -- zone brûlée interdite (s)

-- imitations
C.VOYANT_PERIODE = 2              -- les vrais voyants : 2 s pile
C.VOYANT_FAUX = { 1.6, 2.6 }      -- les siens dérivent dans cette plage
C.IMITATIONS_PAR_PHASE = {
	{ "voyants", "porte" },
	{ "voyants", "porte", "coups", "pas" },
	{ "voyants", "porte", "coups", "pas", "message", "lampe" },
	{ "porte", "coups", "pas", "message", "lampe" },
}

-- taille du corps (studs) pour les collisions et la détection des coups
C.TAILLE_CORPS = Vector3.new(5, 3, 5)
C.ENVERGURE = 12.1

-- sons : identifiants d'assets Roblox à renseigner (bibliothèque du Creator Store). Vide = pas de son.
C.SONS = {
	succion = "", goutte = "", chute = "", bip = "", coups = "", pas = "",
	fouet = "", morsure = "", cri = "", encre = "", brulure = "", mort = "",
	eclabousse = "", remous = "",    -- pas dans l'eau ; sillage de la créature
}

return C
