"""
YEAH THIS WAS STUPID
import discord
import json
from config import PERMSJSON_PATH
from pathlib import Path

class PermLoader():
    def __init__(self, path: Path):
        with open(path, 'r') as f:
            perms_json = json.load(f)

        try:
            self.use_ids: bool = perms_json["use_ids"]
            self._role_hierarchy: list = perms_json["role_hierarchy"]
            
            self.command_perms: dict = perms_json["command_perms"]
        
        except AttributeError:
            raise AttributeError(f"Could not find, user_ids, role_hierarchy, command_perms in {path}")

    def get_allowed_roles(self, minimum_role: str) -> tuple:
        sliced_list: list = []
        found_minimum_role: bool = False

        for i, row in enumerate(self._role_hierarchy):
            if row[1] == minimum_role:
                found_minimum_role = True
                sliced_list = self._role_hierarchy[:i + 1]
                break

        if found_minimum_role == False:
            raise ValueError(f"Could not find {minimum_role} in the hierarchy list")
        

        self.id_hierarchy: tuple
        self.name_hierarchy: tuple
        self.id_hierarchy, self.name_hierarchy = zip(*sliced_list)
        return self.id_hierarchy if self.use_ids else self.name_hierarchy

perms_file: PermLoader = PermLoader(path=PERMSJSON_PATH)

DEPRECIATED
def check_perms(interaction: discord.Interaction, command_name: str):
    if not isinstance(interaction.user, discord.Member):
        raise ValueError("The user could not be resolved.")
    user_roles = interaction.user.roles

    hierarchy_list = id_hierarchy if use_ids else name_hierarchy

    if command_name in command_perms:
        lowest_index_needed = name_hierarchy.index(command_perms[command_name])
    else:
        lowest_index_needed = 99999 #If the command is not in the json file, just allow everyone to use it

    for role in user_roles:
        role_value = role.id if use_ids else role.name
        if role_value not in hierarchy_list:
            continue

        user_index = hierarchy_list.index(role_value)

        if lowest_index_needed > user_index: #If the user index is closer up the list than the minimum needed, return true
            return True
                
    return False
"""