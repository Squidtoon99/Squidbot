import asyncio
import logging
from typing import Iterable, Optional

from discord import Embed, Member, Reaction, User
from discord.ext.commands import CommandError, Context, Paginator

__all__ = ("LinePaginator",)
FIRST_EMOJI = "\u23EE"  # [:track_previous:]
LEFT_EMOJI = "\u2B05"  # [:arrow_left:]
RIGHT_EMOJI = "\u27A1"  # [:arrow_right:]
LAST_EMOJI = "\u23ED"  # [:track_next:]
DELETE_EMOJI = "\u274c"  # [:x:]

PAGINATION_EMOJI = [FIRST_EMOJI, LEFT_EMOJI, RIGHT_EMOJI, LAST_EMOJI, DELETE_EMOJI]

# modifications for server knight


class LinePaginator(Paginator):
    """
    A class that aids in paginating code blocks for Discord messages.
    Attributes
    -----------
    prefix: :class:`str`
        The prefix inserted to every page. e.g. three backticks.
    suffix: :class:`str`
        The suffix appended at the end of every page. e.g. three backticks.
    max_size: :class:`int`
        The maximum amount of codepoints allowed in a page.
    max_lines: :class:`int`
        The maximum amount of lines allowed in a page.
    """

    def __init__(self, prefix="```", suffix="```", max_size=2000, max_lines=None):
        """
        This function overrides the Paginator.__init__
        from inside discord.ext.commands.
        It overrides in order to allow us to configure
        the maximum number of lines per page.
        """
        self.prefix = prefix
        self.suffix = suffix
        self.max_size = max_size - len(suffix)
        self.max_lines = max_lines
        self._current_page = [prefix]
        self._linecount = 0
        self._count = len(prefix) + 1  # prefix + newline
        self._pages = []

    def add_line(self, line="", *, empty=False):
        """Adds a line to the current page.
        If the line exceeds the :attr:`max_size` then an exception
        is raised.
        This function overrides the Paginator.add_line
        from inside discord.ext.commands.
        It overrides in order to allow us to configure
        the maximum number of lines per page.
        Parameters
        -----------
        line: str
            The line to add.
        empty: bool
            Indicates if another empty line should be added.
        Raises
        ------
        RuntimeError
            The line was too big for the current :attr:`max_size`.
        """
        if len(line) > self.max_size - len(self.prefix) - 2:
            raise RuntimeError(
                "Line exceeds maximum page size %s"
                % (self.max_size - len(self.prefix) - 2)
            )

        if self.max_lines is not None:
            if self._linecount >= self.max_lines:
                self._linecount = 0
                self.close_page()

            self._linecount += 1
        if self._count + len(line) + 1 > self.max_size:
            self.close_page()

        self._count += len(line) + 1
        self._current_page.append(line)

        if empty:
            self._current_page.append("")
            self._count += 1

    @classmethod
    async def paginate(
        cls,
        lines: Iterable[str],
        ctx: Context,
        embed: Embed,
        bot,
        prefix: str = "",
        suffix: str = "",
        max_lines: Optional[int] = None,
        max_size: int = 500,
        empty: bool = True,
        restrict_to_user: User = None,
        timeout: int = 300,
        footer_text: str = None,
    ):
        """
        Use a paginator and set of reactions to provide pagination over a set of lines. The reactions are used to
        switch page, or to finish with pagination.
        When used, this will send a message using `ctx.send()` and apply a set of reactions to it. These reactions may
        be used to change page, or to remove pagination from the message. Pagination will also be removed automatically
        if no reaction is added for five minutes (300 seconds).
        >>> embed = Embed()
        >>> embed.set_author(name="Some Operation", url=url, icon_url=icon)
        >>> await LinePaginator.paginate(
        ...     (line for line in lines),
        ...     ctx, embed
        ... )
        :param lines: The lines to be paginated
        :param ctx: Current context object
        :param embed: A pre-configured embed to be used as a template for each page
        :param prefix: Text to place before each page
        :param suffix: Text to place after each page
        :param max_lines: The maximum number of lines on each page
        :param max_size: The maximum number of characters on each page
        :param empty: Whether to place an empty line between each given line
        :param restrict_to_user: A user to lock pagination operations to for this message, if supplied
        :param timeout: The amount of time in seconds to disable pagination of no reaction is added
        :param footer_text: Text to prefix the page number in the footer with
        """

        def event_check(reaction_: Reaction, user_: Member):
            """
            Make sure that this reaction is what we want to operate on
            """

            no_restrictions = (
                # Pagination is not restricted
                not restrict_to_user
                or
                # The reaction was by a whitelisted user
                user_.id == restrict_to_user.id
            )

            return (
                # Conditions for a successful pagination:
                all(
                    (
                        # Reaction is on this message
                        reaction_.message.id == message.id,
                        # Reaction is one of the pagination emotes
                        reaction_.emoji in PAGINATION_EMOJI,
                        # Reaction was not made by the Bot
                        user_.bot is not True,
                        # There were no restrictions
                        no_restrictions,
                    )
                )
            )

        paginator = cls(
            prefix=prefix, suffix=suffix, max_size=max_size, max_lines=max_lines
        )
        current_page = 0
        first = True
        for line in lines:
            if "__" in line and not first:  # if a command starts with ** I'm f'd
                paginator.close_page()
            elif first:
                first = not first

            try:
                paginator.add_line(line, empty=empty)
            except Exception:
                logging.exception(f"Failed to add line to paginator: '{line}'")
                raise  # Should propagate
            else:
                logging.debug(f"Added line to paginator: '{line}'")

        logging.debug(f"Paginator created with {len(paginator.pages)} pages")

        embed.description = paginator.pages[current_page]

        if len(paginator.pages) <= 1:
            if footer_text:
                embed.set_footer(text=footer_text)
                logging.debug(f"Setting embed footer to '{footer_text}'")

            logging.debug(
                "There's less than two pages, so we won't paginate - sending single page on its own"
            )
            return await ctx.send(embed=embed)
        if footer_text:
            embed.set_footer(
                text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
            )
        else:
            embed.set_footer(text=f"Page {current_page + 1}/{len(paginator.pages)}")

        logging.debug(f"Setting embed footer to '{embed.footer.text}'")

        logging.debug("Sending first page to channel...")
        message = await ctx.send(embed=embed)

        logging.debug("Adding emoji reactions to message...")

        async def emojify():
            for emoji in PAGINATION_EMOJI:
                # Add all the applicable emoji to the message
                logging.debug(f"Adding reaction: {repr(emoji)}")
                await message.add_reaction(emoji)

        asyncio.ensure_future(emojify())  # smart buttons

        while True:
            try:
                reaction, user = await bot.wait_for(
                    "reaction_add", timeout=timeout, check=event_check
                )
                logging.debug(f"Got reaction: {reaction}")
            except asyncio.TimeoutError:
                logging.debug("Timed out waiting for a reaction")
                break  # We're done, no reactions for the last 5 minutes

            if reaction.emoji == DELETE_EMOJI:
                logging.debug("Got delete reaction")
                break

            if reaction.emoji == FIRST_EMOJI:
                await message.remove_reaction(reaction.emoji, user)
                current_page = 0

                logging.debug(
                    f"Got first page reaction - changing to page 1/{len(paginator.pages)}"
                )

                embed.description = ""
                await message.edit(embed=embed)
                embed.description = paginator.pages[current_page]
                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )
                await message.edit(embed=embed)

            if reaction.emoji == LAST_EMOJI:
                await message.remove_reaction(reaction.emoji, user)
                current_page = len(paginator.pages) - 1

                logging.debug(
                    f"Got last page reaction - changing to page {current_page + 1}/{len(paginator.pages)}"
                )

                embed.description = ""
                await message.edit(embed=embed)
                embed.description = paginator.pages[current_page]
                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )
                await message.edit(embed=embed)

            if reaction.emoji == LEFT_EMOJI:
                await message.remove_reaction(reaction.emoji, user)

                if current_page <= 0:
                    logging.debug(
                        "Got previous page reaction, but we're on the first page - ignoring"
                    )
                    continue

                current_page -= 1
                logging.debug(
                    f"Got previous page reaction - changing to page {current_page + 1}/{len(paginator.pages)}"
                )

                embed.description = ""
                await message.edit(embed=embed)
                embed.description = paginator.pages[current_page]

                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )

                await message.edit(embed=embed)

            if reaction.emoji == RIGHT_EMOJI:
                await message.remove_reaction(reaction.emoji, user)

                if current_page >= len(paginator.pages) - 1:
                    logging.debug(
                        "Got next page reaction, but we're on the last page - ignoring"
                    )
                    continue

                current_page += 1
                logging.debug(
                    f"Got next page reaction - changing to page {current_page + 1}/{len(paginator.pages)}"
                )

                embed.description = ""
                await message.edit(embed=embed)
                embed.description = paginator.pages[current_page]

                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )

                await message.edit(embed=embed)

        logging.debug("Ending pagination and removing all reactions...")
        try:
            await message.clear_reactions()
        except:
            pass
