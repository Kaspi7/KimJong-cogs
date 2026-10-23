
import discord
from redbot.core import commands


class BasicTools(commands.Cog):
    """Basic utility commands for LawlietBot."""

    @commands.command()
    async def serverinfo(self, ctx):
        """Show information about this server."""
        guild = ctx.guild
        if guild is None:
            await ctx.send("Use this command in a server.")
            return

        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blurple()
        )
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(
            name="Text channels",
            value=len(guild.text_channels)
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):
        """Show information about a member."""
        member = member or ctx.author

        embed = discord.Embed(
            title=str(member),
            color=discord.Color.blurple()
        )
        embed.add_field(name="User ID", value=member.id, inline=False)
        embed.add_field(
            name="Account created",
            value=discord.utils.format_dt(member.created_at, style="D"),
            inline=False
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(BasicTools(bot))
      
