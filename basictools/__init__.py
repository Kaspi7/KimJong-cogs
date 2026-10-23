
import random
import time
from collections import defaultdict, deque

import aiohttp
import discord
from redbot.core import commands, app_commands


class BasicTools(commands.Cog):
    """LawlietBot utilities, fun commands, and basic moderation."""

    def __init__(self, bot):
        self.bot = bot
        self.message_times = defaultdict(deque)
        self.last_spam_warning = {}

    # ---------- SERVER INFORMATION ----------

    @app_commands.command(
        name="serverinfo",
        description="Show information about this server."
    )
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Members",
            value=guild.member_count or "Unknown"
        )
        embed.add_field(
            name="Text channels",
            value=len(guild.text_channels)
        )
        embed.add_field(
            name="Created",
            value=discord.utils.format_dt(guild.created_at, style="D"),
            inline=False,
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await interaction.response.send_message(embed=embed)

    # ---------- USER INFORMATION ----------

    @app_commands.command(
        name="userinfo",
        description="Show information about a server member."
    )
    @app_commands.guild_only()
    @app_commands.describe(member="Member to look up; defaults to you.")
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
        embed.add_field(
            name="Joined server",
            value=(
                discord.utils.format_dt(member.joined_at, style="D")
                if member.joined_at else "Unknown"
            ),
            inline=False,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    # ---------- AVATAR ----------

    @app_commands.command(
        name="avatar",
        description="Show a user's profile picture."
    )
    @app_commands.describe(user="User whose avatar you want to see.")
    async def avatar(
        self,
        interaction: discord.Interaction,
        user: discord.User = None,
    ):
        user = user or interaction.user

        embed = discord.Embed(
            title=f"{user.display_name}'s avatar",
            color=discord.Color.blurple(),
        )
        embed.set_image(url=user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    # ---------- RANDOM CHOICE ----------

    @app_commands.command(
        name="choose",
        description="Choose randomly between options separated by commas."
    )
    @app_commands.describe(options="Example: pizza, burgers, noodles")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [item.strip() for item in options.split(",") if item.strip()]

        if len(choices) < 2:
            await interaction.response.send_message(
                "Give me at least two options separated by commas.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"I choose: **{random.choice(choices)}**"
        )

    # ---------- MAGIC 8-BALL ----------

    @app_commands.command(
        name="8ball",
        description="Ask the magic 8-ball a question."
    )
    @app_commands.describe(question="Your question")
    async def eightball(
        self,
        interaction: discord.Interaction,
        question: str,
    ):
        answers = [
            "Definitely.",
            "Absolutely not.",
            "Probably.",
            "Ask again later.",
            "The odds look good.",
            "I wouldn't count on it.",
            "Signs point to yes.",
            "My sources are unclear.",
            "Bro, that's a mystery.",
            "Without a doubt.",
        ]

        await interaction.response.send_message(
            f"🎱 **Question:** {question}\n"
            f"**Answer:** {random.choice(answers)}"
        )

    # ---------- POLLS ----------

    @app_commands.command(
        name="poll",
        description="Create a yes-or-no poll."
    )
    @app_commands.guild_only()
    @app_commands.describe(question="What do you want members to vote on?")
    async def poll(self, interaction: discord.Interaction, question: str):
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

        message = await interaction.original_response()
        await message.add_reaction("👍")
        await message.add_reaction("👎")

    # ---------- TIMEOUT MODERATION ----------

    @app_commands.command(
        name="timeout",
        description="Temporarily timeout a server member."
    )
    @app_commands.guild_only()
    @app_commands.describe(
        member="Member to timeout",
        minutes="Timeout length in minutes (1 to 10080)",
        reason="Reason for the timeout",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: int,
        reason: str = "No reason provided",
    ):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "You need the Moderate Members permission.",
                ephemeral=True,
            )
            return

        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "I need the Moderate Members permission.",
                ephemeral=True,
            )
            return

        if minutes < 1 or minutes > 10080:
            await interaction.response.send_message(
                "Choose a duration from 1 to 10080 minutes (7 days).",
                ephemeral=True,
            )
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot timeout yourself.",
                ephemeral=True,
            )
            return

        if member.id == self.bot.user.id:
            await interaction.response.send_message(
                "I cannot timeout myself.",
                ephemeral=True,
            )
            return

        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "You cannot timeout someone with an equal or higher role.",
                ephemeral=True,
            )
            return

        try:
            await member.timeout(
                discord.utils.utcnow()
                + discord.timedelta(minutes=minutes),
                reason=reason,
            )
        except AttributeError:
            from datetime import timedelta

            try:
                await member.timeout(
                    timedelta(minutes=minutes),
                    reason=reason,
                )
            except discord.HTTPException:
                await interaction.response.send_message(
                    "Discord rejected the timeout. Check my role and permissions.",
                    ephemeral=True,
                )
                return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the timeout. Check my role and permissions.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Timed out {member.mention} for {minutes} minutes.\n"
            f"Reason: {reason}"
        )

    # ---------- CLEAR MESSAGES ----------

    @app_commands.command(
        name="clear",
        description="Delete a number of recent messages."
    )
    @app_commands.guild_only()
    @app_commands.describe(amount="Number of messages to delete (1 to 100)")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "You need the Manage Messages permission.",
                ephemeral=True,
            )
            return

        if not interaction.channel.permissions_for(
            interaction.guild.me
        ).manage_messages:
            await interaction.response.send_message(
                "I need the Manage Messages permission.",
                ephemeral=True,
            )
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "Choose a number from 1 to 100.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(
                f"Deleted {len(deleted)} messages.",
                ephemeral=True,
            )
        except discord.HTTPException:
            await interaction.followup.send(
                "I couldn't delete those messages.",
                ephemeral=True,
            )

    # ---------- MEMES ----------

    @app_commands.command(
        name="meme",
        description="Fetch a random meme."
    )
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "https://meme-api.com/gimme"
                ) as response:
                    if response.status != 200:
                        raise ValueError("Meme service unavailable")

                    data = await response.json()

            if data.get("nsfw") or not data.get("url"):
                await interaction.followup.send(
                    "Got an unsuitable meme. Try again!"
                )
                return

            embed = discord.Embed(
                title=data.get("title", "Random meme")[:250],
                url=data.get("postLink"),
                color=discord.Color.blurple(),
            )
            embed.set_image(url=data["url"])
            embed.set_footer(
                text=f"From r/{data.get('subreddit', 'memes')}"
            )

            await interaction.followup.send(embed=embed)

        except (aiohttp.ClientError, ValueError, KeyError, TypeError):
            await interaction.followup.send(
                "Couldn't fetch a meme right now. Try again later."
            )

    # ---------- JOKES ----------

    @app_commands.command(
        name="joke",
        description="Get a random joke."
    )
    async def joke(self, interaction: discord.Interaction):
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "I told my computer I needed a break. It said: no problem, I'll go to sleep.",
            "Why did the Discord bot cross the road? It got pinged on the other side.",
            "My Wi-Fi and I have a complicated relationship. It keeps disconnecting.",
            "I tried to make a belt out of watches. It was a waist of time.",
        ]

        await interaction.response.send_message(random.choice(jokes))

    # ---------- ROAST ----------

    @app_commands.command(
        name="roast",
        description="Give someone a playful roast."
    )
    @app_commands.describe(user="Who should get roasted?")
    async def roast(
        self,
        interaction: discord.Interaction,
        user: discord.User = None,
    ):
        user = user or interaction.user

        roasts = [
            "has the processing speed of a potato.",
            "could lose a staring contest with a loading screen.",
            "has more lag than public Wi-Fi.",
            "is the reason instructions have pictures.",
            "has main-character energy in a tutorial.",
            "could confuse a GPS by walking in a straight line.",
        ]

        await interaction.response.send_message(
            f"{user.mention} {random.choice(roasts)}"
        )

    # ---------- SHIP RATING ----------

    @app_commands.command(
        name="ship",
        description="Generate a random compatibility score."
    )
    @app_commands.describe(
        first="First person",
        second="Second person",
    )
    async def ship(
        self,
        interaction: discord.Interaction,
        first: discord.User,
        second: discord.User,
    ):
        score = random.randint(0, 100)

        if score >= 80:
            comment = "Perfect match!"
        elif score >= 60:
            comment = "Looking promising."
        elif score >= 40:
            comment = "Could go either way."
        else:
            comment = "It's complicated."

        await interaction.response.send_message(
            f"💘 **{first.display_name} + {second.display_name}**\n"
            f"Compatibility: **{score}%** — {comment}\n"
            "*Just for fun; not a real compatibility test.*"
        )

    # ---------- RATE SOMETHING ----------

    @app_commands.command(
        name="rate",
        description="Give something a random rating out of 10."
    )
    @app_commands.describe(item="What should I rate?")
    async def rate(self, interaction: discord.Interaction, item: str):
        score = random.randint(1, 10)

        await interaction.response.send_message(
            f"I rate **{item}** a **{score}/10**."
        )

    # ---------- WELCOME MESSAGE ----------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Welcome new members in #general."""
        channel = discord.utils.get(
            member.guild.text_channels,
            name="general",
        )

        if channel is not None:
            try:
                await channel.send(
                    f"Welcome {member.mention} Enjoy your stay!"
                )
            except discord.HTTPException:
                pass

    # ---------- BASIC ANTI-SPAM ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Delete rapid message bursts when possible."""
        if message.author.bot or message.guild is None:
            return

        if not message.guild.me.guild_permissions.manage_messages:
            return

        now = time.monotonic()
        user_key = (message.guild.id, message.author.id)
        timestamps = self.message_times[user_key]

        timestamps.append(now)

        while timestamps and now - timestamps[0] > 6:
            timestamps.popleft()

        if len(timestamps) >= 6:
            timestamps.clear()

            try:
                await message.delete()
            except discord.HTTPException:
                return

            last_warning = self.last_spam_warning.get(user_key, 0)

            if now - last_warning >= 10:
                self.last_spam_warning[user_key] = now

                try:
                    await message.channel.send(
                        f"{message.author.mention}, slow down! "
                        "Please don't spam.",
                        delete_after=5,
                    )
                except discord.HTTPException:
                    pass


async def setup(bot):
    await bot.add_cog(BasicTools(bot))
        
