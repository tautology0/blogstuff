#!/usr/bin/env python3

import statistics
import random
import math
import dice
import names_generator
import os
import pickle
import argparse
import functools
from rich.progress import Progress
from typing import Callable, Iterator

# Murphy's rules 
# https://basicroleplaying.org/topic/23536-whats-the-appeal-for-random-armor-value/

class Warrior:
	def __init__(self, rules, baseattack):
		# link to the rules object so we don't need to pass it all the time
		self.rules = rules
		self.stats = {}
		self.dead = False
		for stat in [ "str", "con", "siz", "int", "pow", "dex", "cha" ]:
			self.stats[stat] = self.rules.roll_stat(stat)
		
		# Set HP
		self.hp = self.rules.calc_hp(self.stats)
		self.loc_hp = self.rules.location_hp(self.hp)
		self.name = names_generator.generate_name().replace("_"," ").title()

		# We don't need to calculate damage bonus, we can do this when hit
		self.weapon="great axe"
		self.attack_bonus = self.rules.attack_bonus(self.stats)
		self.attack_skill = baseattack + random.randrange(1, 10) * 5 + self.attack_bonus
		self.fumble_chance = self.rules.fumble_chance(self.attack_skill)
		self.damage_mod = self.rules.get_damage_mod(self.stats)

	def __repr__(self):
		string = f"Rules: {type(self.rules).__name__}\n"
		string += f"Warrior: {self.name}\n"
		if self.dead:
			string += "Warrior is dead\n"
		for stat in [ "str", "con", "siz", "int", "pow", "dex", "cha" ]:
			string += f" {stat}: {self.stats[stat]}\n"
		string += f" HP: {self.hp}\n"
		for loc in [ "head", "chest", "arm", "abdomen", "leg" ]:
			string += f"  {loc}: {self.loc_hp[loc]} "
		string += f"\nWeapon: {self.weapon}\n"
		string += f"Attack Skill: {self.attack_skill}%  Fumble: {self.fumble_chance}%\n"
		return string
	
	def damage(self, max: bool | None = False) -> int:
		# For now we only support great axe, which is 2d6 + 2
		if max:
			damage = 14 # 2d6 max (12) + 2
		else:
			damage = dice(6) + dice(6) + 2

		# damage bonus
		# Optimized: Using pre-calculated damage mod
		if self.damage_mod == '1d4':
			damage += dice(4)
		elif self.damage_mod == '-1d4':
			damage -= dice(4)
		elif self.damage_mod == '1d6':
			damage += dice(6)
			
		return damage

# implements RQ1 as a base
class RQBase:
	# Roll stats
	def roll_stat(self, stat: str) -> int:
		return dice(6) + dice(6) + dice(6)

	# Calculate hit points
	def calc_hp(self, stats: dict) -> int:
		hp = stats["con"]
		modifier = 0
		if stats["str"] >= 13: modifier += 1
		if stats["str"] >= 17: modifier += 1
		if stats["str"] <=  8: modifier -= 1
		if stats["str"] <=  4: modifier -= 2 
		if stats["pow"] >= 17: modifier += 1
		if stats["pow"] <=  4: modifier -= 1
		hp += modifier
		if hp <= 0: hp = 1
		return hp

	def location_hp(self, hp: int) -> dict:
		loc_hp = {}
		third = math.ceil(hp / 3)
		loc_hp["leg"] = third
		loc_hp["abdomen"] = third
		loc_hp["chest"] = third + 1
		loc_hp["arm"] = third - 1
		loc_hp["head"] = third
		return loc_hp

	def _secondary_stat_bonus(self, stat: int) -> int:
		bonus = 0
		if stat <=  4: bonus -= 5
		if stat >= 17: bonus += 5
		return bonus

	def _primary_stat_bonus(self, stat: int) -> int:
		bonus = self._secondary_stat_bonus(stat)
		if stat <=  8: bonus -= 5
		if stat >= 13: bonus += 5
		return bonus	
		
	def attack_bonus(self, stats: dict) -> int:
		# calculate attack skill bonus
		bonus = 0
		bonus += self._secondary_stat_bonus(stats["str"])
		bonus += self._primary_stat_bonus(stats["int"])
		bonus += self._secondary_stat_bonus(stats["pow"])
		bonus += self._primary_stat_bonus(stats["dex"])
		return bonus

	# is_fumble, returns a fumble result
	def fumble_chance(self, skill: int) -> int:
		if skill >= 81: return 1
		if skill >= 61: return 2
		if skill >= 41: return 3
		if skill >= 21: return 4
		return 5

	def has_hitself(self, warrior) -> int:
		# Look on fumble table, returns damage if any
		# We can ignore impale as you can't fumble and impale
		fumble_roll = dice(100)
		if fumble_roll < 93:
		   return 0
		if 93 <= fumble_roll <= 95:
			return warrior.damage()
		if 96 <= fumble_roll <= 97:
			return warrior.damage(max = True)
		if fumble_roll == 98:
			# Ignore armour here, but we're not doing armour
			return warrior.damage()
		if fumble_roll > 98:
			# Multiple attempts
			damage = 0
			for i in range(fumble_roll - 97):
				damage += self.has_hitself(warrior)
			return damage
		return 0

	def is_head_hit(self, location: int) -> bool:
		return 19 <= location <= 20

	def is_arm_hit(self, location: int) -> bool:
		return 13 <= location <= 18
	
	def is_leg_hit(self, location: int) -> bool:
		return location <= 8
	
	def get_damage_mod(self, stats: dict) -> str:
		value = stats["str"] + stats["siz"]
		if value < 13: return "-1d4"
		if value < 25: return "0"
		if value < 33: return "1d4"
		return "1d6"

class RQ2(RQBase):
	# RQ2 is essentially the same as RQ1
	pass

class RQ3(RQBase):
	# Roll stats
	def roll_stat(self, stat: str) -> int:
		if stat == "int" or stat == "siz": return dice(6) + dice(6) + 6
		return dice(6) + dice(6) + dice(6)

	def calc_hp(self, stats: dict) -> int:
		return math.ceil((stats["con"] + stats["siz"]) / 2)
	
	def location_hp(self, hp: int) -> dict:
		loc_hp = {}
		third = math.ceil(hp / 3)
		loc_hp["leg"] = third
		loc_hp["abdomen"] = third
		loc_hp["chest"] = third + 1
		if hp >= 16: loc_hp["chest"] += 1
		loc_hp["arm"] = third - 1
		if hp >= 10: loc_hp["arm"] -= 1
		loc_hp["head"] = third
		return loc_hp

	def _secondary_stat_bonus(self, stat: int) -> int:
		if stat == 10: return 0
		return (stat - 10) / 2

	def _primary_stat_bonus(self, stat: int) -> int:
		if stat == 10: return 0
		return stat - 10

	def attack_bonus(self, stats: dict) -> int:
		# calculate attack skill bonus
		bonus = 0
		bonus += self._primary_stat_bonus(stats["int"])
		bonus += self._primary_stat_bonus(stats["dex"])
		bonus += self._secondary_stat_bonus(stats["str"])
		return bonus

	# is_fumble, returns a fumble result
	def fumble_chance(self, skill: int) -> int:
		return math.ceil((100 - skill) / 5)

	def has_hitself(self, warrior) -> int:
		# Look on fumble table, returns damage if any
		# We can ignore impale as you can't fumble and impale
		fumble_roll = dice(100)
		if 93 <= fumble_roll <= 95:
			return warrior.damage()
		if 96 <= fumble_roll <= 97:
			return warrior.damage(max = True)
		if fumble_roll == 98:
			# Ignore armour here, but we're not doing armour
			return warrior.damage(max = True)
		if fumble_roll > 98:
			# Multiple attempts
			damage = 0
			for i in range(fumble_roll - 97):
				damage += self.has_hitself(warrior)
			return damage
		return 0

# RQ5 is a weird mix of RQ2 and RQ3
class RQ5(RQBase):
	# Roll stats
	def roll_stat(self, stat: str) -> int:
		if stat == "int" or stat == "siz": return dice(6) + dice(6) + 6
		return dice(6) + dice(6) + dice(6)

	# is_fumble, returns a fumble result
	def fumble_chance(self, skill: int) -> int:
		return math.ceil((100 - skill) / 5)

	def has_hitself(self, warrior) -> int:
		# Look on fumble table, returns damage if any
		# We can ignore impale as you can't fumble and impale
		fumble_roll = dice(100)
		if 93 <= fumble_roll <= 95:
			return warrior.damage()
		if 96 <= fumble_roll <= 97:
			return warrior.damage(max = True)
		if fumble_roll == 98:
			# Do slashing damage and ignore armour
			return warrior.damage() + warrior.damage()
		if fumble_roll > 98:
			# Multiple attempts
			damage = 0
			for i in range(fumble_roll - 97):
				damage += self.has_hitself(warrior)
			return damage
		return 0

	def is_head_hit(self, location: int) -> bool:
		return 19 <= location <= 20

	def is_arm_hit(self, location: int) -> bool:
		return 13 <= location <= 18
	
	def is_leg_hit(self, location: int) -> bool:
		return location <= 8
	
	def get_damage_mod(self, stats: dict) -> str:
		value = stats["str"] + stats["siz"]
		if value < 13: return "-1d4"
		if value < 25: return "0"
		if value < 33: return "1d4"
		return "1d6"

def calc_round(warrior):
	res = 0
	roll = dice(100)
	if roll > (100 - warrior.fumble_chance):
		#print(f"{roll} {100 - warrior.fumble_chance}")
		damage = warrior.rules.has_hitself(warrior)
		if damage > 0:
			location = dice(20)
			if warrior.rules.is_head_hit(location):
				if damage > (warrior.loc_hp["head"] * 2) + 5:
					res = 1
			elif warrior.rules.is_arm_hit(location):
				if damage > (warrior.loc_hp["arm"] * 2) + 5:
					res = 2
			elif warrior.rules.is_leg_hit(location):
				if damage > (warrior.loc_hp["leg"] * 2) + 5:
					res = 2
	return res

def parseargs():
	parser = argparse.ArgumentParser()

	parser.add_argument('--rules', type=str, default='RQ2')
	parser.add_argument('--men', type=int, default=1000)
	parser.add_argument('--battles', type=int, default=5)
	parser.add_argument('--minutes', type=int, default=2)
	parser.add_argument('--baseattack', type=int, default=40)
	parser.add_argument('--cache', action=argparse.BooleanOptionalAction, default=True)

	args = parser.parse_args()
	return args

args = parseargs()

# set up partial dice helper function
dice=functools.partial(random.randint, 1)

rounds = int((args.minutes / 5) * 25)
men = args.men
battles = args.battles

print(f"Repeating experiment {args.battles} times")

match(args.rules):
	case "RQ2":	rules = RQ2()
	case "RQ3": rules = RQ3()
	case "RQ5": rules = RQ5()
	case _:
		print(f"Unknown ruleset: {rules}")
		exit
	
if args.rules == "RQ2":
	rules = RQ2()
elif args.rules == "RQ3":
	rules = RQ3()

print(f"Using rules {type(rules).__name__}")
warriors = []
print(f"Generating our fierce army of {args.men} warriors")
if args.cache and os.path.isfile("warriors.cache"):
	# Load warriors from cache
	with open("warriors.cache", "rb") as cache:
		warriors = pickle.load(cache)
	print(f"[Loading cached warriors, warriors now set to {len(warriors)}]")
else:
	for warrior in range(1, args.men + 1):
		warriors.append(Warrior(rules, args.baseattack))
	with open("warriors.cache", "wb") as cache:
		pickle.dump(warriors, cache)

# lists for storing results for each go
headcounts = []
limbcounts = []

progress = Progress()
progress.start()
battle_progress = progress.add_task("[red]Battles...", total=args.battles)
round_progress = progress.add_task("[green]Rounds...", total=rounds)
warrior_progress = progress.add_task("[cyan]Warriors...", total=len(warriors))

for battle in range(args.battles):
	progress.update(round_progress, completed=0)
	headlosses = []
	limblosses = []
	for round in range(1, rounds):
		# Optimized: Calling progress update once per round instead of per warrior
		progress.update(warrior_progress, completed=0)
		for warrior in warriors:
			if warrior.dead:
				continue
			res = calc_round(warrior)
			if res == 1:
				headlosses.append(warrior.name)
				warrior.dead = True
			elif res == 2:
				limblosses.append(warrior.name)
				warrior.dead = True
		progress.update(warrior_progress, completed=len(warriors))
		progress.update(round_progress, advance=1)

	headcounts.append(len(headlosses))
	limbcounts.append(len(limblosses))
	progress.update(battle_progress, advance=1)

progress.stop()

print(f"Mean head losses: {statistics.fmean(headcounts)}")	
print(f"Mean limb losses: {statistics.fmean(limbcounts)}")