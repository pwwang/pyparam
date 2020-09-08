"""Classes for completions"""
import os
import sys
import re
import textwrap
from functools import lru_cache
from typing import Optional, Iterator, List, Callable, Type, Union, Tuple
from pathlib import Path
from hashlib import sha256

class Completer:
    """Main completion handler

    Attributes:
        comp_shell: The shell where the completion will be conducted
            One of ['', 'bash', 'fish', 'zsh']
            Obtained from environment
        comp_words: The words have been entered before completion
        comp_curr: The current word for completion
        comp_prev: The previous word matched
    """

    def __init__(self):
        """Constructor

        Read the environment variables
        """
        complete_prepared = self._prepare_complete()

        self.comp_shell: str = complete_prepared[0]
        self.comp_words: Optional[List[str]] = (
            complete_prepared[1] if self.comp_shell else None
        )
        self.comp_curr: Optional[str] = (
            complete_prepared[2] if self.comp_shell else None
        )
        self.comp_prev: Optional[str] = (
            None if not self.comp_shell or not self.comp_words
            else self.comp_words[-1]
        )

    @property
    def progvar(self) -> str:
        """Get the program name that can be used as a variable"""
        return re.sub(r'[^\w_]+', '', self.prog)

    @property
    def uid(self) -> str:
        """Get the uid based on the raw program name

        This is used as the prefix or suffix of some shell function names
        """
        return sha256(self.prog.encode()).hexdigest()[:6]

    def _prepare_complete(self) -> Tuple[
            str, Optional[List[str]], Optional[str]
    ]:
        """Prepare for completion, get the env variables"""
        env_name: str = f"{self.progvar}_COMPLETE_SHELL_{self.uid}".upper()
        shell: str = os.environ.get(env_name, '')
        if not shell:
            return shell, None, ''

        comp_words: List[str] = os.environ['COMP_WORDS'].split()
        comp_cword: int = int(os.environ['COMP_CWORD'] or 0)

        has_python: bool = 'python' in Path(comp_words[0]).stem
        if has_python and len(comp_words) == 1:
            sys.exit(0)

        is_module: bool = has_python and comp_words[1] == '-m'
        if is_module and (len(comp_words) < 3 or comp_words[2] != self.prog):
            sys.exit(0)

        if has_python and not is_module and comp_words[1] != self.prog:
            sys.exit(0)

        current: str = ''
        if comp_cword < len(comp_words):
            comp_words.pop(comp_cword)

        comp_words = comp_words[
            (3 if is_module else 2 if has_python else 1):
        ]
        return shell, comp_words, current

    def _post_complete(self, completions) -> Optional[str]:
        """Post processing the completions

        Filter only completions with given current word/prefix
        If non-fish, don't give the description
        """
        if completions is None or not completions:
            return

        for comp in completions:
            if comp.startswith(self.comp_curr):
                yield (comp.split('\t')[0]
                       if self.comp_shell != 'fish' else comp)

    @lru_cache()
    def _all_params(self) -> List[Type['Param']]:
        """All parameters under this command

        self.params don't have all of them, since namespaced ones are under
        namespace paramters
        """
        ret: List[Type['Param']] = []
        ret_append: Callable = ret.append
        for param in self.params.values():
            if param not in ret:
                ret_append(param)
            if param.type == 'ns':
                ret.extend(param.decendents)
        return ret

    def generate(self,
                 shell: str,
                 python: Optional[str] = None,
                 module: bool = False) -> None:
        """Generate the shell code to be integrated

        For bash, it should be appended to ~/.profile
        For zsh, it should be appended to ~/.zprofile
        For fish, it should be appended to
            ~/.config/fish/completions/{prog}.fish
            If python is provided, this should go to `python.fish` rather than
            the `{prog}.fish`

        Args:
            shell: The shell to generate the code for.
            python: The python name or path to invoke completion.
            module: Whether do completion for `python -m <prog>`

        Raises:
            ValueError: if shell is not one of bash, zsh and fish
        """

        if shell == 'zsh':
            print(self._generate_zsh(python=python, module=module))
        elif shell == 'fish':
            print(self._generate_fish(python=python, module=module))
        elif shell == 'bash':
            print(self._generate_bash(python=python, module=module))
        else:
            raise ValueError(f'Shell not supported: {shell}')

    def _generate_bash(self, python: Optional[str], module: bool) -> str:
        # type: (Optional[str]) -> str
        """Generate the shell code for bash"""
        env_name: str = f"{self.progvar}_COMPLETE_SHELL_{self.uid}".upper()
        complete_exec: str = (
            "$1" if not python
            else f"$1 {self.prog}" if not module
            else f"$1 -m {self.prog}"
        )
        func_name: str = f"_{self.progvar}_completion_{self.uid}"
        code: str = f"""\
            {func_name}()
            {{
                COMPREPLY=( $( COMP_WORDS="${{COMP_WORDS[*]}}" \\
                            COMP_CWORD=$COMP_CWORD \\
                            {env_name}=bash {complete_exec} \\
                            2>/dev/null ) )
            }}
            complete -o default -F {func_name} {python or self.prog}
        """
        return textwrap.dedent(code)

    def _generate_fish(self, python: Optional[str], module: bool) -> str:
        # type: (Optional[str]) -> str
        """Generate the shell code for fish"""
        env_name: str = f"{self.progvar}_COMPLETE_SHELL_{self.uid}".upper()
        complete_exec: str = (
            "$COMP_WORDS[1]" if not python
            else f"$COMP_WORDS[1] {self.prog}" if not module
            else f"$COMP_WORDS[1] -m {self.prog}"
        )
        func_name: str = f"__fish_complete_{self.progvar}_{self.uid}"
        code: str = f"""\
            function {func_name}
                set -lx COMP_WORDS (commandline -o) ""
                set -lx COMP_CWORD ( \\
                    math (contains -i -- (commandline -t) $COMP_WORDS)-1 \\
                )
                set -lx {env_name} fish
                string split \\  -- (eval {complete_exec})
            end
            complete -fa "({func_name})" -c {python or self.prog}
        """
        return textwrap.dedent(code)

    def _generate_zsh(self, python: Optional[str], module: str) -> str:
        # type: (Optional[str]) -> str
        """Generate the shell code for zsh"""
        env_name: str = f"{self.progvar}_COMPLETE_SHELL_{self.uid}".upper()
        complete_exec: str = (
            "$words[1]" if not python
            else f"$words[1] {self.prog}" if not module
            else f"$words[1] -m {self.prog}"
        )
        func_name: str = f"_{self.progvar}_completion_{self.uid}"
        code: str = f"""\
            function {func_name} {{
                local words cword
                read -Ac words
                read -cn cword
                reply=( $( COMP_WORDS="$words[*]" \\
                           COMP_CWORD=$(( cword-1 )) \\
                           {env_name}=zsh {complete_exec} \\
                           2>/dev/null ))
            }}
            compctl -K {func_name} {python or self.prog}
        """
        return textwrap.dedent(code)

    def _parse_completed(self) -> Tuple[
            Optional[List[Type['Param']]], Optional[bool],
            Optional[str], Optional[List[str]]
    ]:
        """Parse completed parameters/commands, and give
        the rest unmatched words. If command matched, also return the command

        Returns:
            A tuple of:
                - A list of completed parameters.
                - A boolean value indicating whether all required parameters
                    has been completed
                - Command name if a command matched
                - Rest of words after the command is matched
        """
        for i, word in enumerate(self.comp_words):
            if word in self.commands:
                return None, None, word, self.comp_words[i+1:]

        unmatched_required: bool = False
        matched: List[Type['Param']] = []
        matched_append: Callable = matched.append
        for param in self._all_params():
            if any(param._prefix_name(name) in self.comp_words
                   for name in param.names):
                matched_append(param)
            elif param.required:
                unmatched_required = True

        return matched, not unmatched_required, None, None

    def complete(self) -> Iterator[str]:
        """Yields the completions

        Yields:
            The strings as completion candidates
        """
        yield from self._post_complete(self._complete())

    def _complete(self) -> Iterator[str]:
        """Provide the completion candidates

        The rules are:
        1. When there are uncompleted required parameters, don't give command
           candidates
        2. Otherwise, give both command and parameter candidates
        """
        (completed, all_required_completed,
         command, rest) = self._parse_completed()

        if command:
            self.commands[command].comp_shell = self.comp_shell
            self.commands[command].comp_words = rest
            self.commands[command].comp_curr = self.comp_curr
            self.commands[command].comp_prev = rest[-1] if rest else None
            # make sure that help parameters or commands are added
            self.commands[command].parse()
            return

        # If you just entered a parameter name with prefix
        prev_matched: List[Type['Param']] = [
            param for param in self._all_params()
            if any(param._prefix_name(name) == self.comp_prev
                   for name in param.names)
        ]
        completions: Optional[Union[str, Iterator[str]]] = ''
        if prev_matched:
            completions = prev_matched[0].complete(self.comp_curr)

        if completions is None:
            return
        if completions:
            yield from completions
            return

        for param in self._all_params():
            if param.type == 'ns':
                continue
            if param in completed and not param.complete_relapse:
                continue

            param_comp_desc: str = param.desc[0].splitlines()[0].replace(
                ' ', '\t'
            )
            for name in param.names:
                yield f"{param._prefix_name(name)}\t{param_comp_desc}"

        if all_required_completed:
            # see if we have any commands
            for command_name, command in self.commands.items():
                yield (
                    f"{command_name}\t"
                    f"{command.desc[0].splitlines()[0].replace(' ', chr(9))}"
                )

class CompleterParam: # pylint: disable=too-few-public-methods
    """Class for a parameter dealing with completion"""
    complete_relapse: bool = False

    def complete(self, current: str) -> Optional[Union[str, Iterator[str]]]:
        """Give the completion candidates

        Args:
            current: Current prefix

        Returns:
            None when there are no candidates, nor should we have next
                paramters/commands as candidates.
                An empty string if we should put next parameters/commands
                as candidates. Otherwise an Iterator of candidates
        """
