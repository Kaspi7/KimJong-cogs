import os
import aiohttp
import random
import re
import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from redbot.core import commands, app_commands


class BasicTools(commands.Cog):
    """LawlietBot utility, moderation, welcome, anti-spam and fun commands."""

    def __init__(self, bot):
        self.bot = bot
        self.message_times = defaultdict(deque)
        self.last_auto_reply = defaultdict(float)

    # ---------- Permission checks ----------

    async def moderator_check(self, interaction, permission):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command only works in a server.",
                ephemeral=True,
            )
            return False

        if not getattr(interaction.user.guild_permissions, permission, False):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True,
            )
            return False

        return True

    # ---------- Basic slash commands ----------

    @app_commands.command(name="serverinfo", description="Show server information")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Use this command in a server.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Server ID", value=str(guild.id), inline=False)
        embed.add_field(
            name="Members",
            value=str(guild.member_count or "Unknown"),
        )
        embed.add_field(
            name="Text channels",
            value=str(len(guild.text_channels)),
        )
        embed.add_field(
            name="Voice channels",
            value=str(len(guild.voice_channels)),
        )
        embed.add_field(
            name="Created",
            value=discord.utils.format_dt(guild.created_at, style="D"),
            inline=False,
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show information about a member")
    @app_commands.describe(member="Member to inspect; leave empty for yourself")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None,
    ):
        member = member or interaction.user

        embed = discord.Embed(
            title=str(member),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="User ID", value=str(member.id), inline=False)
        embed.add_field(
            name="Account created",
            value=discord.utils.format_dt(member.created_at, style="D"),
            inline=False,
        )

        if isinstance(member, discord.Member):
            joined = (
                discord.utils.format_dt(member.joined_at, style="D")
                if member.joined_at
                else "Unknown"
            )
            embed.add_field(name="Joined server", value=joined, inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Show a user's avatar")
    @app_commands.describe(member="User whose avatar you want to see")
    async def avatar(
        self,
        interaction: discord.Interaction,
        member: discord.User = None,
    ):
        member = member or interaction.user

        embed = discord.Embed(
            title=f"{member}'s avatar",
            color=discord.Color.blurple(),
        )
        embed.set_image(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="choose", description="Choose between options")
    @app_commands.describe(options="Separate your choices with |")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [item.strip() for item in options.split("|") if item.strip()]

        if len(choices) < 2:
            await interaction.response.send_message(
                "Give me at least two choices separated by |.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"I choose: **{random.choice(choices)}**"
        )

    @app_commands.command(name="8ball", description="Ask the magic 8-ball")
    @app_commands.describe(question="Ask a question")
    async def eightball(self, interaction: discord.Interaction, question: str):
        answers = [
            "Definitely.",
            "No doubt about it.",
            "Looks promising.",
            "Ask again later.",
            "Hard to tell right now.",
            "Probably not.",
            "Absolutely not.",
            "The 8-ball is confused. Try again.",
        ]
        await interaction.response.send_message(
            f"🎱 {random.choice(answers)}"
        )

    @app_commands.command(name="poll", description="Create a yes/no poll")
    @app_commands.describe(question="What do you want people to vote on?")
    async def poll(self, interaction: discord.Interaction, question: str):
        await interaction.response.send_message(
            f"📊 **Poll:** {question}\n\nReact with 👍 for Yes or 👎 for No."
        )

        message = await interaction.original_response()

        try:
            await message.add_reaction("👍")
            await message.add_reaction("👎")
        except discord.HTTPException:
            pass

    # ---------- Moderation commands ----------

    @app_commands.command(name="clear", description="Delete recent messages")
    @app_commands.describe(amount="Number of messages to delete, from 1 to 100")
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ):
        if not await self.moderator_check(interaction, "manage_messages"):
            return

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Use this command in a text channel.",
                ephemeral=True,
            )
            return

        me = interaction.guild.get_member(self.bot.user.id)
        if me is None or not channel.permissions_for(me).manage_messages:
            await interaction.response.send_message(
                "I need the Manage Messages permission.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await channel.purge(limit=amount)
            await interaction.followup.send(
                f"Deleted {len(deleted)} message(s).",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Discord denied permission to delete messages.",
                ephemeral=True,
            )
        except discord.HTTPException:
            await interaction.followup.send(
                "Couldn't delete those messages.",
                ephemeral=True,
            )

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(
        member="Member to timeout",
        minutes="Duration in minutes, from 1 to 10080",
        reason="Reason for the timeout",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 10080],
        reason: str = "No reason provided",
    ):
        if not await self.moderator_check(interaction, "moderate_members"):
            return

        guild = interaction.guild
        moderator = interaction.user
        me = guild.get_member(self.bot.user.id)

        if member.id == moderator.id:
            await interaction.response.send_message(
                "You can't timeout yourself.",
                ephemeral=True,
            )
            return

        if member.id == guild.owner_id:
            await interaction.response.send_message(
                "You can't timeout the server owner.",
                ephemeral=True,
            )
            return

        if moderator.id != guild.owner_id and member.top_role >= moderator.top_role:
            await interaction.response.send_message(
                "Your highest role must be above that member's highest role.",
                ephemeral=True,
            )
            return

        if me is None or not me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "I need the Moderate Members permission.",
                ephemeral=True,
            )
            return

        if member.top_role >= me.top_role:
            await interaction.response.send_message(
                "My highest role must be above that member's highest role.",
                ephemeral=True,
            )
            return

        try:
            await member.timeout(timedelta(minutes=minutes), reason=reason)
            await interaction.response.send_message(
                f"Timed out {member.mention} for {minutes} minute(s).\n"
                f"Reason: {reason}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord denied permission to timeout that member.",
                ephemeral=True,
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                "Couldn't apply the timeout.",
                ephemeral=True,
            )

    @app_commands.command(name="untimeout", description="Remove a member's timeout")
    @app_commands.describe(member="Member whose timeout you want to remove")
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        if not await self.moderator_check(interaction, "moderate_members"):
            return

        guild = interaction.guild
        moderator = interaction.user
        me = guild.get_member(self.bot.user.id)

        if moderator.id != guild.owner_id and member.top_role >= moderator.top_role:
            await interaction.response.send_message(
                "Your highest role must be above that member's highest role.",
                ephemeral=True,
            )
            return

        if me is None or not me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "I need the Moderate Members permission.",
                ephemeral=True,
            )
            return

        if member.top_role >= me.top_role:
            await interaction.response.send_message(
                "My highest role must be above that member's highest role.",
                ephemeral=True,
            )
            return

        try:
            await member.timeout(None, reason=f"Timeout removed by {moderator}")
            await interaction.response.send_message(
                f"Removed the timeout for {member.mention}."
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord denied permission to remove that timeout.",
                ephemeral=True,
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                "Couldn't remove that timeout.",
                ephemeral=True,
            )

    @app_commands.command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(seconds="Delay in seconds, from 0 to 21600; 0 disables it")
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
    ):
        if not await self.moderator_check(interaction, "manage_channels"):
            return

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Use this command in a text channel.",
                ephemeral=True,
            )
            return

        me = interaction.guild.get_member(self.bot.user.id)
        if me is None or not channel.permissions_for(me).manage_channels:
            await interaction.response.send_message(
                "I need the Manage Channels permission.",
                ephemeral=True,
            )
            return

        try:
            await channel.edit(slowmode_delay=seconds)
            if seconds == 0:
                await interaction.response.send_message("Slowmode disabled.")
            else:
                await interaction.response.send_message(
                    f"Slowmode set to {seconds} second(s)."
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord denied permission to change slowmode.",
                ephemeral=True,
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                "Couldn't change slowmode.",
                ephemeral=True,
            )

    # ---------- Welcome message ----------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = discord.utils.get(
            member.guild.text_channels,
            name="general",
        )

        if channel is None:
            return

        me = member.guild.get_member(self.bot.user.id)
        if me is None or not channel.permissions_for(me).send_messages:
            return

        try:
            await channel.send(
                f"Welcome {member.mention} Enjoy your stay!",
                allowed_mentions=discord.AllowedMentions(
                    users=True,
                    roles=False,
                    everyone=False,
                ),
            )
        except discord.HTTPException:
            pass

    # ---------- Anti-spam and funny replies ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        now = time.monotonic()
        key = (message.guild.id, message.author.id)
        timestamps = self.message_times[key]

        while timestamps and now - timestamps[0] > 6:
            timestamps.popleft()

        timestamps.append(now)

        # Delete a rapid burst of messages when possible.
        if len(timestamps) >= 6:
            me = message.guild.get_member(self.bot.user.id)

            if me and message.channel.permissions_for(me).manage_messages:
                try:
                    await message.delete()
                    timestamps.clear()
                except discord.HTTPException:
                    pass

            return

        # The original jokes you chose — unchanged.
        replies = {
            "hello": [
                "HELLOOO. Please remain calm. I am only 73% operational.",
                "Oh look, a living human. What's up? 💀",
                "Greetings, earthling. Your Wi-Fi password, please. Kidding.",
            ],
            "hi": [
                "Hiiii. I was doing absolutely nothing.",
                "Yo. The council has been expecting you.",
                "Hi bro. I bring absolutely no wisdom.",
            ],
            "bro": [
                "BRO 💀",
                "Why am I being summoned like a side quest?",
                "Bro said bro. Cinema.",
            ],
            "lol": [
                "Glad my suffering entertains you.",
                "LMAOOO. I need financial compensation for this.",
                "💀💀 someone save this conversation.",
            ],
            "lmao": [
                "YOUR HONOR, THEY'RE LAUGHING AT ME.",
                "I'm putting this in my villain origin story.",
                "NAHHH 😭",
            ],
            "help": [
                "Help with what, bro? My life is already a side quest.",
                "Support ticket received. Emotional support unavailable.",
                "I'm listening. My two brain cells are ready.",
            ],
            "bored": [
                "Have you tried staring at a wall? Very advanced gameplay.",
                "Go bother someone. Preferably someone who deserves it.",
                "Boredom detected. Deploying absolutely nothing.",
            ],
            "good morning": [
                "MORNING. Time to pretend we're productive.",
                "Good morning. Who approved this early access to life?",
                "Rise and shine. Or just rise. Shining is optional.",
            ],
            "good night": [
                "Night bro. Don't let the lag monsters bite.",
                "Sleep well. I'll be here judging everyone's messages.",
                "Logging off? Weak. Go recharge your human battery.",
            ],
            "thanks": [
                "You're welcome, citizen.",
                "No problem. Payment accepted in imaginary cookies.",
                "Anytime, bro. My invoice is in the mail.",
            ],
            "thank you": [
                "You're welcome. I expect a statue in my honor.",
                "No worries. I live to serve. Unfortunately.",
                "Glad I could help, bro.",
            ],
            "who are you": [
                "I'm LawlietBot. Professional yapper, amateur genius.",
                "Your local digital menace.",
                "A bunch of code with suspicious confidence.",
            ],
            "are you stupid": [
                "I prefer the term computationally adventurous.",
                "And yet you asked me. Interesting strategy. 💀",
                "My lawyer advised me not to answer that.",
            ],
        }

        content = message.content.lower().strip()

        for phrase, options in replies.items():
            if not re.search(
                r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                content,
            ):
                continue

            # Avoid replying to every matching message.
            channel_key = (message.guild.id, message.channel.id)

            if now - self.last_auto_reply[channel_key] < 8:
                return

            if random.random() > 0.65:
                return

            self.last_auto_reply[channel_key] = now

            try:
                await message.channel.send(
                    random.choice(options),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass

            return


async def setup(bot):
    await bot.add_cog(BasicTools(bot))
        
