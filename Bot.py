import discord
from discord import app_commands
from discord.ext import commands
import random
import io
import re
import os
from flask import Flask
import threading

# ---------------- Flask keepalive ----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running ✅"

def run_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

# ---------------- Discord bot setup ----------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- Obfuscator functions ----------------
def rand_name(length):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choice(chars) for _ in range(length))

def encode_string(s):
    return "{" + ",".join(str(ord(c)) for c in s) + "}"

def junk_vars():
    code = ""
    for _ in range(random.randint(3,6)):
        var = rand_name(random.randint(5,10))
        code += f"local {var}={random.randint(100,999)}\n"
    return code

def junk_funcs():
    code = ""
    for _ in range(random.randint(2,4)):
        func = rand_name(random.randint(5,10))
        var = rand_name(random.randint(5,10))
        code += f"local function {func}()\n"
        code += f"  local {var}={random.randint(1,999)}\n"
        code += f"  for i=1,{random.randint(2,5)} do {var}={var}+{random.randint(1,10)} end\n"
        code += f"  return {var}\n"
        code += f"end\n"
    return code

def fake_loop():
    var = rand_name(random.randint(5,10))
    return f"for {var}=1,{random.randint(2,10)} do {var}={var}*{random.randint(1,5)} end\n"

def obfuscate(lua_code):
    obf = ""
    for line in lua_code.splitlines():
        for _ in range(random.randint(3,5)):
            obf += junk_vars() + junk_funcs() + fake_loop()
        encoded = encode_string(line)
        pcall_count = random.randint(1,3)
        for _ in range(pcall_count):
            obf += "pcall(function()\n"
        obf += f"  local s={encoded}\n"
        obf += "  for i=1,#s do s[i]=string.char(s[i]) end\n"
        obf += "  loadstring(table.concat(s,''))()\n"
        for _ in range(pcall_count):
            obf += "end)\n"
    return obf

def deobfuscate(obf_code):
    """
    Reverse our obfuscation by extracting Lua code
    encoded as {number,number,...}.
    """
    pattern = re.compile(r'local s=\{([0-9,]+)\}')
    result_lines = []
    for match in pattern.findall(obf_code):
        chars = [chr(int(x)) for x in match.split(',')]
        result_lines.append(''.join(chars))
    return '\n'.join(result_lines)

# ---------------- Bot events ----------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}!")

# ---------------- Slash Commands ----------------
@bot.tree.command(name="obfuscate", description="Obfuscate a Lua file")
@app_commands.describe(file="The Lua file you want to obfuscate")
async def obfuscate_command(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer()
    lua_code = await file.read()
    lua_code = lua_code.decode("utf-8")
    obf_code = obfuscate(lua_code)
    output_file = io.BytesIO(obf_code.encode("utf-8"))
    await interaction.followup.send(file=discord.File(output_file, filename="obfuscated.lua"))

@bot.tree.command(name="deobfuscate", description="Deobfuscate a Lua file obfuscated by this bot")
@app_commands.describe(file="The obfuscated Lua file")
async def deobfuscate_command(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer()
    obf_code = await file.read()
    obf_code = obf_code.decode("utf-8")
    try:
        lua_code = deobfuscate(obf_code)
        output_file = io.BytesIO(lua_code.encode("utf-8"))
        await interaction.followup.send(file=discord.File(output_file, filename="deobfuscated.lua"))
    except Exception as e:
        await interaction.followup.send(f"Failed to deobfuscate: {e}")

@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Lua Obfuscator Bot Commands:**\n"
        "1. `/obfuscate [file]` - Obfuscate a Lua file and receive an obfuscated Lua file.\n"
        "2. `/deobfuscate [file]` - Deobfuscate a Lua file obfuscated by this bot.\n"
        "3. `/help` - Show this help message."
    )
    await interaction.response.send_message(help_text)

# ---------------- Run Flask + Bot ----------------
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
