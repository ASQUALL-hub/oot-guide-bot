"""Hand-written explanations of what items, songs and story steps do, for build_game.py.

Everything with a number (ammo, magic cost, age limits, damage, ranges) is NOT typed here: build_game.py takes it
from the game code (data/meta/game_rules.json) or the ROM. These are the plain-language parts the code can't
say by itself. They are labeled `curated` in game.json so a bot can tell them apart from code-derived facts.

ITEMS: ITEM enum name -> (display name, randomizer item name or None, how to use it, what it does).
The randomizer name links the item to the logic (where it is found, what it unlocks).
"""

C = "C button (assign it on the Select Item page)"
EQ = "equipment page: highlight it and press A"
PASSIVE = "passive: works as soon as you have it"
QUEST = "quest status: works as soon as you have it"

ITEMS = {
    "ITEM_DEKU_STICK": ("Deku Stick", "Deku Stick Capacity", C,
                        "Swing it like a sword (often as strong as a Master Sword slash; see each enemy's damage table). Hold it in a lit torch to set it on "
                        "fire, then touch other torches or webs to burn them. It burns down after a while and breaks on hard "
                        "hits. Child only."),
    "ITEM_DEKU_NUT": ("Deku Nut", "Deku Nut Capacity", C,
                      "Throw it: the flash stuns most nearby enemies (no damage). Useful to stun Gohma, Deku Scrubs and Lizalfos."),
    "ITEM_BOMB": ("Bomb", "Bomb Bag", C,
                  "Press its C button to pull one out. While carrying it, A, B or any C button throws it if Link is moving "
                  "(speed 1.1 or more) and sets it down if he is standing still (Player_CanThrowCarriedActor in z_player.c). "
                  "It explodes after a fuse. Blows open cracked walls and floors, rocks, bombable grottos, and hurts most "
                  "enemies. Needs a Bomb Bag."),
    "ITEM_BOW": ("Fairy Bow", "Bow", C,
                 "Hold the C button to aim (first person or while locked on), release to shoot. Hits eye switches, "
                 "targets and enemies at range. Adult only. Needs arrows (quiver)."),
    "ITEM_ARROW_FIRE": ("Fire Arrow", "Fire Arrows", C,
                        "Arrow wrapped in fire: lights torches from a distance, burns webs, hurts enemies weak to fire. Red ice needs Blue Fire instead. Uses magic per shot."),
    "ITEM_DINS_FIRE": ("Din's Fire", "Dins Fire", C,
                       "A dome of fire around Link: lights every torch in range, burns webs and hurts everything nearby. Uses magic."),
    "ITEM_SLINGSHOT": ("Fairy Slingshot", "Slingshot", C,
                       "Shoots Deku Seeds: hits eye switches, crystal switches, Gold Skulltulas and weak enemies from afar. Child only."),
    "ITEM_OCARINA_FAIRY": ("Fairy Ocarina", "Ocarina", C,
                           "Press its C button to play. Plays every song Link knows (see songs)."),
    "ITEM_OCARINA_OF_TIME": ("Ocarina of Time", "Ocarina", C,
                             "Same as the Fairy Ocarina for playing songs. Getting it teaches the Song of Time, which opens the Door of Time."),
    "ITEM_BOMBCHU": ("Bombchu", None, C,
                     "A bomb on wheels. It is always set down, never thrown (Player_CanThrowCarriedActor); then it runs "
                     "forward along floors and up walls and explodes when it hits something."),
    "ITEM_HOOKSHOT": ("Hookshot", "Progressive Hookshot", C,
                      "Fires a chain. On a hookshot target surface (wood, some panels, targets: `hookshotable` in the "
                      "collision surfaces) it pulls Link to that spot; on chests and small items it pulls them back; on enemies it "
                      "stuns or hurts. Adult only."),
    "ITEM_LONGSHOT": ("Longshot", "Progressive Hookshot", C, "Hookshot with twice the reach."),
    "ITEM_ARROW_ICE": ("Ice Arrow", "Ice Arrows", C, "Arrow that freezes many enemies solid. Uses magic per shot. Not needed in the original game."),
    "ITEM_FARORES_WIND": ("Farore's Wind", "Farores Wind", C,
                          "Inside a dungeon: first use sets a warp point where Link stands; using it again takes you back "
                          "there (or lets you set a new one). Uses magic."),
    "ITEM_BOOMERANG": ("Boomerang", "Boomerang", C,
                       "Thrown at the aimed or locked-on target and comes back: stuns enemies, grabs items, hits switches. Child only."),
    "ITEM_LENS_OF_TRUTH": ("Lens of Truth", "Lens of Truth", C,
                           "While on, shows invisible platforms, enemies and chests and lets you see through fake walls "
                           "and floors. Drains magic while active."),
    "ITEM_MAGIC_BEAN": ("Magic Bean", "Magic Bean", C,
                        "Plant one in a soft soil patch as child (stand on it, press the C button). Seven years later, adult "
                        "Link can ride the leaf platform that grew there. Bugs released on soft soil reveal a Gold Skulltula."),
    "ITEM_HAMMER": ("Megaton Hammer", "Megaton Hammer", C,
                    "Heavy swing: presses rusted floor switches, smashes boulders, wooden stakes and statues, knocks "
                    "down certain walls and pillars. Adult only."),
    "ITEM_ARROW_LIGHT": ("Light Arrow", "Light Arrows", C,
                         "Arrow of light: dispels the barriers at the end of Ganon's Castle trials (Demo_Kekkai is hit only "
                         "by light arrows) and stuns Ganondorf and Ganon. Uses magic per shot."),
    "ITEM_NAYRUS_LOVE": ("Nayru's Love", "Nayrus Love", C, "A crystal barrier that makes Link take no damage for a while. Uses magic."),
    "ITEM_BOTTLE_EMPTY": ("Empty Bottle", "Bottle", C,
                          "Swing it (press its C button) to catch a fairy, bug, fish, Blue Fire, Poe, or scoop water. A full "
                          "bottle on a C button is drunk/used/released when pressed."),
    "ITEM_BOTTLE_POTION_RED": ("Red Potion", None, C, "Drink: refills all health."),
    "ITEM_BOTTLE_POTION_GREEN": ("Green Potion", None, C, "Drink: refills all magic."),
    "ITEM_BOTTLE_POTION_BLUE": ("Blue Potion", None, C, "Drink: refills health and magic."),
    "ITEM_BOTTLE_FAIRY": ("Bottled Fairy", None, C,
                          "Drink or release: heals. If Link dies with a fairy in a bottle, it revives him automatically."),
    "ITEM_BOTTLE_FISH": ("Fish", None, C, "Release it in front of Lord Jabu-Jabu (child) to be swallowed into his belly."),
    "ITEM_BOTTLE_MILK_FULL": ("Lon Lon Milk", None, C, "Drink: heals 5 hearts. Two drinks per bottle."),
    "ITEM_BOTTLE_RUTOS_LETTER": ("Ruto's Letter", "Rutos Letter", C,
                                 "Show it to King Zora (press its C button in front of him): he moves aside, opening the way to "
                                 "Zora's Fountain and Jabu-Jabu. Afterwards it becomes an empty bottle."),
    "ITEM_BOTTLE_BLUE_FIRE": ("Blue Fire", None, C,
                              "Pour it on red ice to melt it (frees King Zora, opens Ice Cavern and Gerudo Training Ground paths)."),
    "ITEM_BOTTLE_BUG": ("Bug", None, C, "Release over a soft soil patch to make a Gold Skulltula appear."),
    "ITEM_BOTTLE_BIG_POE": ("Big Poe", None, C, "Sell to the Poe Collector in the Market guard house (adult). 10 of them win a bottle."),
    "ITEM_BOTTLE_MILK_HALF": ("Half Lon Lon Milk", None, C, "Drink: heals 5 hearts, leaves an empty bottle."),
    "ITEM_BOTTLE_POE": ("Poe", None, C, "Drink: random effect (heals or hurts). Sells for rupees."),
    "ITEM_WEIRD_EGG": ("Weird Egg", "Weird Egg", C, "Child trade item: hatches into a Cucco at the next dawn (the rooster crow; code: z_kankyo.c)."),
    "ITEM_CHICKEN": ("Cucco", None, C, "Child trade item: use it on sleeping Talon at Hyrule Castle to wake him; then you can climb into the castle grounds."),
    "ITEM_ZELDAS_LETTER": ("Zelda's Letter", "Zeldas Letter", C,
                           "Show it to the guard at the Death Mountain gate in Kakariko to open it; later, show it at the "
                           "Happy Mask Shop to start the mask trade."),
    "ITEM_MASK_KEATON": ("Keaton Mask", "Keaton Mask", C, "Mask trade (sell to the Kakariko gate guard). Wearing masks changes what some people say."),
    "ITEM_MASK_SKULL": ("Skull Mask", "Skull Mask", C, "Mask trade (sell to the Skull Kid in Lost Woods). Wearing it for the Deku Theater wins a Deku Stick upgrade."),
    "ITEM_MASK_SPOOKY": ("Spooky Mask", "Spooky Mask", C, "Mask trade (sell to the graveyard kid)."),
    "ITEM_MASK_BUNNY_HOOD": ("Bunny Hood", "Bunny Hood", C, "Mask trade (sell to the running man in Hyrule Field). No speed boost in this game: z_player.c only draws the ears."),
    "ITEM_MASK_GORON": ("Goron Mask", "Goron Mask", C, "Borrowed after the first four masks are sold. No gameplay effect."),
    "ITEM_MASK_ZORA": ("Zora Mask", "Zora Mask", C, "Borrowed after the first four masks are sold. No gameplay effect."),
    "ITEM_MASK_GERUDO": ("Gerudo Mask", "Gerudo Mask", C, "Borrowed after the first four masks are sold. No gameplay effect."),
    "ITEM_MASK_TRUTH": ("Mask of Truth", "Mask of Truth", C,
                        "Wear it to read Gossip Stones' thoughts and animals' minds; wearing it at the Deku Theater wins a Deku Nut upgrade."),
    "ITEM_POCKET_EGG": ("Pocket Egg", "Pocket Egg", C, "Adult trade item: hatches into the Pocket Cucco at the next dawn."),
    "ITEM_POCKET_CUCCO": ("Pocket Cucco", None, C, "Adult trade item: wake Talon in the Kakariko house, then give it to the Cucco lady for Cojiro."),
    "ITEM_COJIRO": ("Cojiro", "Cojiro", C, "Adult trade item: give to the poacher in Lost Woods for the Odd Mushroom."),
    "ITEM_ODD_MUSHROOM": ("Odd Mushroom", "Odd Mushroom", C, "Adult trade item: take to the potion shop old woman in Kakariko (it spoils if you take too long)."),
    "ITEM_ODD_POTION": ("Odd Potion", "Odd Potion", C, "Adult trade item: give to the poacher's friend in Lost Woods for the Poacher's Saw."),
    "ITEM_POACHERS_SAW": ("Poacher's Saw", "Poachers Saw", C, "Adult trade item: give to the head carpenter in Gerudo Valley for the Broken Goron's Sword."),
    "ITEM_BROKEN_GORONS_SWORD": ("Broken Goron's Sword", "Broken Sword", C, "Adult trade item: take to Biggoron on Death Mountain for the Prescription."),
    "ITEM_PRESCRIPTION": ("Prescription", "Prescription", C, "Adult trade item: take to King Zora for the Eyeball Frog."),
    "ITEM_EYEBALL_FROG": ("Eyeball Frog", "Eyeball Frog", C, "Adult trade item: take to the Lake Hylia lab scientist (time limit) for Eye Drops."),
    "ITEM_EYE_DROPS": ("Eye Drops", "Eyedrops", C, "Adult trade item: take to Biggoron (time limit) for the Claim Check."),
    "ITEM_CLAIM_CHECK": ("Claim Check", "Claim Check", C, "Adult trade item: give to Biggoron (after waiting) for Biggoron's Sword."),
    "ITEM_SWORD_KOKIRI": ("Kokiri Sword", "Kokiri Sword", EQ,
                          "Child's sword on the B button. NOT equipped automatically when picked up: equip it on the "
                          "equipment page. Weakest sword."),
    "ITEM_SWORD_MASTER": ("Master Sword", None, EQ,
                          "Adult sword, equipped automatically when pulled from the pedestal. Pulling or returning it in the "
                          "Temple of Time switches Link between child and adult (time travel)."),
    "ITEM_SWORD_BIGGORON": ("Biggoron's Sword", "Biggoron Sword", EQ, "Two-handed, strongest sword, never breaks. No shield while held. Adult only."),
    "ITEM_GIANTS_KNIFE": ("Giant's Knife", "Giants Knife", EQ, "Two-handed, strong sword bought from Medigoron. Breaks after some hits (then hits like the Kokiri Sword). Adult only."),
    "ITEM_SHIELD_DEKU": ("Deku Shield", "Deku Shield", EQ, "Blocks attacks (hold R). Burns up if touched by fire. Child only. Needed (with the Kokiri Sword) to get past Mido."),
    "ITEM_SHIELD_HYLIAN": ("Hylian Shield", "Hylian Shield", EQ, "Blocks attacks, doesn't burn. Usable at both ages."),
    "ITEM_SHIELD_MIRROR": ("Mirror Shield", "Mirror Shield", EQ,
                           "Blocks attacks and reflects light beams onto sun switches and mirrors (Spirit Temple) and "
                           "magic back at Twinrova. Adult only."),
    "ITEM_TUNIC_KOKIRI": ("Kokiri Tunic", None, EQ, "Default clothes."),
    "ITEM_TUNIC_GORON": ("Goron Tunic", "Goron Tunic", EQ, "Protects from heat: without it, very hot rooms (Fire Temple, crater) count down a timer and kill Link. Adult only."),
    "ITEM_TUNIC_ZORA": ("Zora Tunic", "Zora Tunic", EQ, "Lets Link breathe underwater (no drowning timer). Adult only."),
    "ITEM_BOOTS_KOKIRI": ("Kokiri Boots", None, EQ, "Default boots."),
    "ITEM_BOOTS_IRON": ("Iron Boots", "Iron Boots", EQ,
                        "Heavy: Link sinks and walks on the bottom of water, isn't pushed by wind or currents. Slow (see actions.json speed limits). Adult only."),
    "ITEM_BOOTS_HOVER": ("Hover Boots", "Hover Boots", EQ,
                         "Let Link keep walking on air for a short time after leaving an edge, but give almost no traction "
                         "(see actions.json). Adult only."),
    "ITEM_BULLET_BAG_30": ("Bullet Bag", None, PASSIVE, "Holds Deku Seeds for the Slingshot (comes with it)."),
    "ITEM_QUIVER_30": ("Quiver", None, PASSIVE, "Holds arrows (comes with the Bow)."),
    "ITEM_BOMB_BAG_20": ("Bomb Bag", "Bomb Bag", PASSIVE, "Lets Link carry bombs. Larger bags hold more."),
    "ITEM_STRENGTH_GORONS_BRACELET": ("Goron's Bracelet", "Progressive Strength Upgrade", PASSIVE,
                                      "Lets child Link pull Bomb Flowers and lift them (press A). Also lets him lift some rocks."),
    "ITEM_STRENGTH_SILVER_GAUNTLETS": ("Silver Gauntlets", "Progressive Strength Upgrade", PASSIVE,
                                       "Adult can lift and push big silver blocks and boulders (Spirit Temple, Ganon's Castle, Zora's Fountain)."),
    "ITEM_STRENGTH_GOLD_GAUNTLETS": ("Golden Gauntlets", "Progressive Strength Upgrade", PASSIVE,
                                     "Adult can lift the biggest black/gold pillars (Ganon's Castle, Zora's Fountain grotto)."),
    "ITEM_SCALE_SILVER": ("Silver Scale", "Progressive Scale", PASSIVE, "Press A while swimming to dive deeper (picks up things from deeper water)."),
    "ITEM_SCALE_GOLDEN": ("Golden Scale", "Progressive Scale", PASSIVE, "Dives even deeper than the Silver Scale."),
    "ITEM_ADULTS_WALLET": ("Adult's Wallet", "Progressive Wallet", PASSIVE, "Raises the rupee limit."),
    "ITEM_GIANTS_WALLET": ("Giant's Wallet", "Progressive Wallet", PASSIVE, "Raises the rupee limit again."),
    "ITEM_DEKU_STICK_UPGRADE_20": ("Deku Stick upgrade", "Deku Stick Capacity", PASSIVE, "Carry more Deku Sticks."),
    "ITEM_DEKU_NUT_UPGRADE_30": ("Deku Nut upgrade", "Deku Nut Capacity", PASSIVE, "Carry more Deku Nuts."),
    "ITEM_STONE_OF_AGONY": ("Stone of Agony", "Stone of Agony", QUEST, "Makes the controller rumble near hidden grottos and secrets. The randomizer's logic requires it for hidden grottos."),
    "ITEM_GERUDOS_CARD": ("Gerudo's Membership Card", "Gerudo Membership Card", QUEST,
                          "Gerudos stop attacking; opens the gate to the Haunted Wasteland and lets you into the Gerudo Training Ground and horseback archery."),
    "ITEM_SKULL_TOKEN": ("Gold Skulltula Token", "Gold Skulltula Token", QUEST, "Counts toward the rewards in the House of Skulltula in Kakariko (10, 20, 30, 40, 50, 100)."),
    "ITEM_HEART_CONTAINER": ("Heart Container", "Heart Container", QUEST, "+1 heart of maximum health (from each boss)."),
    "ITEM_HEART_PIECE": ("Piece of Heart", "Piece of Heart", QUEST, "Four of them make one more heart."),
    "ITEM_DUNGEON_BOSS_KEY": ("Boss Key", None, QUEST, "Opens the boss door of the dungeon it was found in."),
    "ITEM_DUNGEON_COMPASS": ("Compass", None, QUEST, "Shows chests and the boss on the dungeon map."),
    "ITEM_DUNGEON_MAP": ("Dungeon Map", None, QUEST, "Shows the dungeon's rooms on the pause map."),
    "ITEM_SMALL_KEY": ("Small Key", None, QUEST, "Opens one locked door in the dungeon it was found in (used up)."),
    "ITEM_MEDALLION_FOREST": ("Forest Medallion", "Forest Medallion", QUEST, "From Phantom Ganon. Counts toward the Rainbow Bridge (all six) and Nocturne/Light Arrow cutscenes."),
    "ITEM_MEDALLION_FIRE": ("Fire Medallion", "Fire Medallion", QUEST, "From Volvagia."),
    "ITEM_MEDALLION_WATER": ("Water Medallion", "Water Medallion", QUEST, "From Morpha."),
    "ITEM_MEDALLION_SPIRIT": ("Spirit Medallion", "Spirit Medallion", QUEST, "From Twinrova."),
    "ITEM_MEDALLION_SHADOW": ("Shadow Medallion", "Shadow Medallion", QUEST, "From Bongo Bongo."),
    "ITEM_MEDALLION_LIGHT": ("Light Medallion", "Light Medallion", QUEST, "From Rauru the first time Link becomes adult."),
    "ITEM_KOKIRI_EMERALD": ("Kokiri's Emerald", "Kokiri Emerald", QUEST, "From the Great Deku Tree. One of the three Spiritual Stones that open the Door of Time."),
    "ITEM_GORON_RUBY": ("Goron's Ruby", "Goron Ruby", QUEST, "From Darunia after King Dodongo."),
    "ITEM_ZORA_SAPPHIRE": ("Zora's Sapphire", "Zora Sapphire", QUEST, "From Ruto after Barinade."),
}

# Songs: OCARINA_SONG enum -> (name, randomizer name, effect). Notes come from the game code.
SONGS = {
    "OCARINA_SONG_LULLABY": ("Zelda's Lullaby", "Zeldas Lullaby",
                             "Triggers ocarina spots marked with the Triforce symbol: the waterfall at the end of Zora's River, "
                             "the Water Temple water level, the Royal Family's Tomb, Great Fairy fountains and spots in several "
                             "dungeons (see ocarina_spots), plus some doors and NPCs."),
    "OCARINA_SONG_EPONAS": ("Epona's Song", "Eponas Song",
                            "At Lon Lon Ranch as adult it calls Epona so you can win her; afterwards it calls her in Hyrule Field "
                            "and other open areas. Played to a cow, it gives milk."),
    "OCARINA_SONG_SARIAS": ("Saria's Song", "Sarias Song",
                            "Talks to Saria (hints). Played to Darunia (child) it makes him dance and give the Goron's Bracelet. "
                            "Played to the Skull Kid in Lost Woods it gives a Piece of Heart."),
    "OCARINA_SONG_SUNS": ("Sun's Song", "Suns Song",
                          "Switches day and night (where time flows). Freezes ReDeads and Gibdos. Next to a Gossip Stone it "
                          "makes a fairy appear (so do Zelda's Lullaby, Epona's Song and the Song of Time: logic "
                          "can_summon_gossip_fairy)."),
    "OCARINA_SONG_TIME": ("Song of Time", "Song of Time",
                          "Opens the Door of Time (with the three Spiritual Stones). Makes blue Song of Time blocks appear or "
                          "vanish (one in Dampe's grave opens the way to the Kakariko windmill as adult)."),
    "OCARINA_SONG_STORMS": ("Song of Storms", "Song of Storms",
                            "Makes it rain. Opens hidden grottos marked 'Song of Storms' (Door_Ana); played in the Kakariko "
                            "windmill as child it drains the well."),
    "OCARINA_SONG_MINUET": ("Minuet of Forest", "Minuet of Forest", "Warp to the Sacred Forest Meadow."),
    "OCARINA_SONG_BOLERO": ("Bolero of Fire", "Bolero of Fire", "Warp to Death Mountain Crater."),
    "OCARINA_SONG_SERENADE": ("Serenade of Water", "Serenade of Water", "Warp to Lake Hylia."),
    "OCARINA_SONG_REQUIEM": ("Requiem of Spirit", "Requiem of Spirit", "Warp to the Desert Colossus (child can reach the Spirit Temple this way)."),
    "OCARINA_SONG_NOCTURNE": ("Nocturne of Shadow", "Nocturne of Shadow", "Warp to the Graveyard (Shadow Temple entrance)."),
    "OCARINA_SONG_PRELUDE": ("Prelude of Light", "Prelude of Light", "Warp to the Temple of Time."),
    "OCARINA_SONG_SCARECROW_SPAWN": ("Scarecrow's Song", "Scarecrow Song",
                                     "Your own 8-note song, taught to the scarecrow (Bonooru) at Lake Hylia as child. As adult, playing it "
                                     "near a hidden scarecrow spot makes Pierre appear as a hookshot target."),
}

# The story in the order the original game expects it. `check` is a logic location or event name; build_game.py
# looks up which playthrough sphere it is in-logic, so the order and what each step needs are verified by the logic.
MAIN_QUEST = [
    ("Get a sword and shield", ["KF Kokiri Sword Chest", "event:Showed Mido Sword & Shield"],
     "Kokiri Sword: crawl through the hole in Kokiri Forest's training area to the chest. Deku Shield: buy it in the Kokiri Shop "
     "(40 rupees). Equip both, then Mido lets you pass to the Great Deku Tree."),
    ("Inside the Deku Tree", ["Deku Tree Slingshot Chest", "Queen Gohma"],
     "Slingshot is in the Deku Tree. Burn the web over the basement with a lit Deku Stick, defeat Queen Gohma (stun her "
     "eye with the slingshot or a Deku Nut, then slash). Reward: Kokiri's Emerald."),
    ("Leave the forest", ["LW Gift from Saria"], "Saria gives the Fairy Ocarina on the bridge out of Kokiri Forest."),
    ("Hyrule Castle and Zelda", ["HC Malon Egg", "HC Zeldas Letter", "Song from Impa"],
     "Malon gives the Weird Egg; it hatches into a Cucco that wakes Talon. Climb into the castle grounds, sneak to "
     "Zelda: Zelda's Letter. Impa teaches Zelda's Lullaby."),
    ("Death Mountain and the Gorons", ["event:Kakariko Village Gate Open", "Song from Saria", "GC Darunias Joy"],
     "Show Zelda's Letter at the Kakariko gate. Learn Saria's Song in the Sacred Forest Meadow and play it to Darunia: Goron's Bracelet."),
    ("Dodongo's Cavern", ["Dodongos Cavern Bomb Bag Chest", "King Dodongo"],
     "Use Bomb Flowers (bracelet) to open the cave; the Bomb Bag is inside. King Dodongo: throw bombs into his mouth, then "
     "slash. Reward: Goron's Ruby."),
    ("Zora's Domain and Jabu-Jabu", ["LH Underwater Item", "Deliver Rutos Letter", "Barinade"],
     "Play Zelda's Lullaby at the waterfall in Zora's River. Ruto's Letter (bottle) is under Lake Hylia: show it to King "
     "Zora, catch a fish, release it before Jabu-Jabu. The Boomerang is inside; Barinade needs it. Reward: Zora's Sapphire."),
    ("Door of Time", ["HF Ocarina of Time Item", "Song from Ocarina of Time", "Master Sword Pedestal", "ToT Reward from Rauru"],
     "Zelda throws the Ocarina of Time into the castle moat (you learn the Song of Time). In the Temple of Time, play it "
     "with the three stones to open the Door, pull the Master Sword: Link is adult. Rauru gives the Light Medallion."),
    ("Forest Temple", ["Graveyard Dampe Race Hookshot Chest", "Sheik in Forest", "Forest Temple Bow Chest", "Phantom Ganon"],
     "Hookshot: win Dampe's race inside his grave (as adult, pull the gravestone back to open it). Minuet of Forest from Sheik. Bow inside the "
     "temple. Phantom Ganon: shoot him with arrows, then return his energy balls. Reward: Forest Medallion."),
    ("Fire Temple", ["GC Rolling Goron as Adult", "Sheik in Crater", "Fire Temple Megaton Hammer Chest", "Volvagia"],
     "Goron Tunic from Link the Goron in Goron City (or buy one). Bolero of Fire. Megaton Hammer inside. Volvagia: hammer its "
     "head when it pops out. Reward: Fire Medallion."),
    ("Ice Cavern and Water Temple", ["ZD King Zora Thawed", "Ice Cavern Iron Boots Chest", "Sheik in Ice Cavern",
                                     "Water Temple Longshot Chest", "Morpha"],
     "Thaw King Zora with Blue Fire for the Zora Tunic. Iron Boots in the Ice Cavern. In the Water Temple play Zelda's Lullaby "
     "on Triforce marks to change the water level; the Longshot is past Dark Link. Morpha: hookshot its nucleus out. Reward: Water Medallion."),
    ("Bottom of the Well and Shadow Temple", ["Sheik in Kakariko", "event:Drain Well", "Bottom of the Well Lens of Truth Chest",
                                              "Shadow Temple Hover Boots Chest", "Bongo Bongo"],
     "Nocturne of Shadow in Kakariko. As child, play the Song of Storms in the windmill to drain the well: the Lens of Truth "
     "is at its bottom. Hover Boots in the Shadow Temple. Bongo Bongo: stun its hands, then its eye. Reward: Shadow Medallion."),
    ("Gerudo Fortress and Spirit Temple", ["Hideout Gerudo Membership Card", "Sheik at Colossus", "Spirit Temple Silver Gauntlets Chest",
                                           "Spirit Temple Mirror Shield Chest", "Twinrova"],
     "Free the four carpenters for the Gerudo card, cross the Haunted Wasteland to the Desert Colossus: Requiem of Spirit. "
     "Do the child half (Silver Gauntlets) and the adult half (Mirror Shield) of the Spirit Temple. Twinrova: reflect one "
     "sister's magic at the other with the Mirror Shield. Reward: Spirit Medallion."),
    ("Light Arrows", ["ToT Light Arrows Cutscene"], "With the Shadow and Spirit Medallions, return to the Temple of Time: Zelda gives the Light Arrows."),
    ("Ganon's Castle", ["event:Ganons Tower Access", "Ganons Tower Boss Key Chest", "Ganon"],
     "The six medallions make the Rainbow Bridge. Clear the six trials (Light Arrows on each barrier), climb the tower, "
     "beat Ganondorf (Light Arrows, then sword), then Ganon (Light Arrows to stun, Master Sword on the tail)."),
]

TRADE_QUESTS = {
    "child": ["Weird Egg", "Cucco (hatches from the egg)", "wake Talon at Hyrule Castle (lets you climb in)", "Zelda's Letter",
              "Kakariko gate opens; Happy Mask Shop lends masks", "Keaton Mask -> Skull Mask -> Spooky Mask -> Bunny Hood -> "
              "Goron/Zora/Gerudo masks and the Mask of Truth"],
    "adult": ["Pocket Egg (Anju, Kakariko)", "Pocket Cucco", "Cojiro (after waking Talon in Kakariko)", "Odd Mushroom (Lost Woods)",
              "Odd Potion (Kakariko potion shop)", "Poacher's Saw (Lost Woods)", "Broken Goron's Sword (Gerudo Valley carpenter)",
              "Prescription (Biggoron)", "Eyeball Frog (King Zora)", "Eye Drops (Lake Hylia lab)", "Claim Check (Biggoron)",
              "Biggoron's Sword"],
}

MENUS = dict(
    open="Press START. It is refused during scene transitions, cutscenes (Play_InCsMode), game over, while the magic bar "
         "is filling, and during the shooting gallery and bombchu bowling games (KaleidoSetup_Update in z_kaleido_setup.c).",
    pages="Four pages in a ring: Select Item -> (R) Map -> (R) Quest Status -> (R) Equipment -> (R) Select Item. "
          "Z goes the other way. Within a scene the menu reopens on the last page used; loading a new scene resets it to "
          "Select Item (KaleidoSetup_Init sets pageIndex = PAUSE_ITEM).",
    item_page="A 6 x 4 grid. Slot number = row * 6 + column (row 0 at the top, column 0 at the left); `slot` in game.json "
              "items gives each item's slot. Move the cursor with the stick, then press C-left, C-down or C-right to put "
              "the item on that C button. Items the current age can't use are greyed out and can't be assigned.",
    equipment_page="A 4 x 4 grid. Rows: 0 swords, 1 shields, 2 tunics, 3 boots. Column 0 shows upgrades (bullet bag/quiver, "
                   "bomb bag, strength, scale) and can't be selected for equipping; columns 1-3 are the three items of that row "
                   "in the order Kokiri/Master/Biggoron, Deku/Hylian/Mirror, Kokiri/Goron/Zora, Kokiri/Iron/Hover. Press A to equip.",
    b_button="The B button holds the sword. Equipping a sword puts it on B. The Kokiri Sword is NOT put on B when you pick it up; "
             "the Master Sword is (code: Item_Give in z_parameter.c).",
    close="Press START again.",
)
