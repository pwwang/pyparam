"""Classes for completions

The idea is inspired from
https://github.com/pallets/click/pull/1622

Some of the code is borrowing there, under following LICENSE:

Copyright 2014 Pallets

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.
Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import os
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Generator,
    Iterator,
    List,
    Tuple,
    Union,
)

if TYPE_CHECKING:
    from .param import Param

COMPLETION_SCRIPT_BASH = """
%(complete_func)s() {
    local IFS=$'\\n'
    local response
    response=$( env COMP_WORDS="${COMP_WORDS[*]}" \\
                COMP_CWORD=$COMP_CWORD \\
                %(complete_shell_var)s=bash %(complete_script)s )
    for completion in $response; do
        IFS=$'\\t' read value type <<< "$completion"
        if [[ $type == 'dir' ]]; then
            COMREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMREPLY=()
            compopt -o filenames
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done
     return 0
}
complete -o default -F %(complete_func)s %(script_name)s
"""

COMPLETION_SCRIPT_ZSH = """
#compdef %(script_name)s
%(complete_func)s() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[%(script_name)s] )) && return 1
    response=("${(@f)$( env COMP_WORDS=\"${words[*]}\" \\
                        COMP_CWORD=$((CURRENT-1)) \\
                        %(complete_shell_var)s=\"zsh\" \\
                        %(complete_script)s )}")
    for key type descr in ${response}; do
      if [[ "$type" == "plain" ]]; then
        if [[ "$descr" == "" ]]; then
          completions+=("$key")
        else
          completions_with_descriptions+=("$key":"$descr")
        fi
      elif [[ "$type" == "dir" ]]; then
        _path_files -/
      elif [[ "$type" == "file" ]]; then
        _path_files -f
      fi
    done
     if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi
     if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
    compstate[insert]="menucomplete"
}
compdef %(complete_func)s %(script_name)s
"""

COMPLETION_SCRIPT_FISH = """
function %(complete_func)s_complete;
    set -l response;
    set -lx COMP_WORDS (commandline -op)
    set -lx COMP_CWORD ( \\
        math (contains -i -- (commandline -t) $COMP_WORDS; or echo 0)-1 \\
    )
    set -lx %(complete_shell_var)s fish
    eval %(complete_script)s | while read completion
        echo $completion | read -d (echo -e "\\t") -l -a metadata
        if [ "$metadata[2]" = "dir" ];
            __fish_complete_directories $metadata[1] | sed "s#^#$metadata[3]#";
        else if [ "$metadata[2]" = "file" ];
            __fish_complete_path $metadata[1] | sed "s#^#$metadata[3]#";
        else if [ "$metadata[2]" = "plain" ];
            echo -n $metadata[1];
            echo -ne "\\t";
            echo $metadata[3];
        end;
    end;
end;

# Don't do complete until <prog> is hit
function %(complete_func)s_condition;
    set -l COMP_WORDS (commandline -op)
    set -l comp_script %(complete_script)s
    set -l len_words (count $COMP_WORDS)
    set -l len_script (count $comp_script)
    set -l incomplete (commandline -t)
    if [ $len_script -eq 1 ];
        return 0;
    end
    # we haven't hit the script or module
    # go ahead do the complete only when
    # len_words > len_script
    # if len_words == len_script, then requires incomplete == ""
    if [ $len_words -lt $len_script ]
        return 1
    else if [ $len_words -eq $len_script -a -n "$incomplete" ]
        return 1
    else if [ $len_script -eq 2 ]
        [ "$COMP_WORDS[2]" = "$comp_script[2]" ]; and return 0; or return 1
    else if [ $len_script -eq 3 ]
        [ "$COMP_WORDS[2]" = "-m" -a "$comp_script[3]" = "$COMP_WORDS[3]" ]; \\
            and return 0; or return 1
    end
    return 1
end;

complete --no-files --command %(script_name)s \\
    --condition "%(complete_func)s_condition" \\
    --arguments "(%(complete_func)s_complete)"
"""


def split_arg_string(string: str) -> List[str]:
    """Given an argument string this attempts to split it into small parts.

    Borrowed from
    https://github.com/pallets/click/blob/3984f9efce5a0d15f058e1abe1ea808c6abd243a/src/click/parser.py#L106

    Args:
        string: The string to be split

    Returns:
        List of split pieces
    """
    ret: List[str] = []
    for match in re.finditer(
        r"('([^'\\]*(?:\\.[^'\\]*)*)'|"
        r"\"([^\"\\]*(?:\\.[^\"\\]*)*)\"|\S+)\s*",
        string,
        re.S,
    ):
        arg = match.group().strip()
        if arg[:1] == arg[-1:] and arg[:1] in "\"'":
            arg = (
                arg[1:-1]
                .encode("ascii", "backslashreplace")
                .decode("unicode-escape")
            )
        try:
            arg = type(string)(arg)
        except UnicodeError:  # pragma: no cover
            pass
        ret.append(arg)
    return ret


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
        self.comp_words: List[str] = (
            complete_prepared[1] if self.comp_shell else None
        )
        self.comp_curr: str = complete_prepared[2] if self.comp_shell else None
        self.comp_prev: str = (
            None
            if not self.comp_shell or not self.comp_words
            else self.comp_words[-1]
        )

    @property
    def progvar(self) -> str:
        """Get the program name that can be used as a variable"""
        return re.sub(r"[^\w_]+", "", self.prog)

    @property
    def uid(self) -> str:
        """Get the uid based on the raw program name

        This is used as the prefix or suffix of some shell function names
        """
        return sha256(self.prog.encode()).hexdigest()[:6]

    def _prepare_complete(
        self,
    ) -> Tuple[str, List[str], str]:
        """Prepare for completion, get the env variables"""
        env_name: str = f"{self.progvar}_COMPLETE_SHELL_{self.uid}".upper()
        shell: str = os.environ.get(env_name, "")
        if not shell:
            return shell, None, ""

        comp_words: List[str] = split_arg_string(os.environ["COMP_WORDS"])
        comp_cword: int = int(os.environ["COMP_CWORD"] or 0)

        current: str = ""
        if comp_cword >= 0:
            try:
                current = comp_words[comp_cword]
            except IndexError:
                pass

        has_python: bool = "python" in Path(comp_words[0]).stem
        if has_python and len(comp_words) == 1:
            sys.exit(0)

        is_module: bool = has_python and comp_words[1] == "-m"
        if is_module and (len(comp_words) < 3 or comp_words[2] != self.prog):
            sys.exit(0)

        if has_python and not is_module and comp_words[1] != self.prog:
            sys.exit(0)

        comp_words = comp_words[(3 if is_module else 2 if has_python else 1) :]

        if current and comp_words and comp_words[-1] == current:
            comp_words.pop(-1)

        if shell == "bash" and comp_words:
            # bash splits '--choice=' to ['--choice'] and '=', and
            # '--choice=l' to ['--choice', '='] and 'l'
            # We can't distinguish if user really enters '--choice=' or
            # '--choice =', but this is the best way to implement this.
            # Also, bash doesn't replace the current,
            # so we just need to get the unfinished part
            if current == "=":
                current = ""  # force the unfinished part
            elif current and comp_words[-1] == "=" and len(comp_words) > 1:
                # pop out the '=' so to force th unfinished part
                comp_words.pop()

        return shell, comp_words, current

    def _post_complete(
        self, completions: Iterator[Tuple[str, str, str]]
    ) -> Generator:
        """Post processing the completions

        Filter only completions with given current word/prefix
        If non-fish, don't give the description
        """
        for comp in completions:
            if self.comp_shell == "fish":
                yield "\t".join(comp)
            elif self.comp_shell == "zsh":
                yield "\n".join((comp[0] or " ", comp[1], comp[2]))
            else:
                yield "\t".join((comp[0] or " ", comp[1]))

    def shellcode(
        self, shell: str, python: str = None, module: bool = False
    ) -> str:
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

        if shell == "zsh":
            return self._shellcode_zsh(python=python, module=module)
        if shell == "fish":
            return self._shellcode_fish(python=python, module=module)
        if shell == "bash":
            return self._shellcode_bash(python=python, module=module)
        raise ValueError(f"Shell not supported: {shell}")

    def _shellcode_bash(self, python: str, module: bool) -> str:
        """Generate the shell code for bash"""
        complete_shell_var: str = (
            f"{self.progvar}_COMPLETE_SHELL_{self.uid}"
        ).upper()
        complete_script: str = (
            "$1"
            if not python
            else f"$1 {self.prog}"
            if not module
            else f"$1 -m {self.prog}"
        )
        complete_func: str = f"_{self.progvar}_completion_{self.uid}"
        return COMPLETION_SCRIPT_BASH % dict(
            complete_func=complete_func,
            complete_shell_var=complete_shell_var,
            complete_script=complete_script,
            script_name=python or self.prog,
        )

    def _shellcode_fish(self, python: str, module: bool) -> str:
        """Generate the shell code for fish"""
        complete_shell_var: str = (
            f"{self.progvar}_COMPLETE_SHELL_{self.uid}"
        ).upper()
        complete_script: str = (
            "$COMP_WORDS[1]"
            if not python
            else f"$COMP_WORDS[1] {self.prog}"
            if not module
            else f"$COMP_WORDS[1] -m {self.prog}"
        )
        complete_func: str = f"__fish_{self.progvar}_{self.uid}"
        return COMPLETION_SCRIPT_FISH % dict(
            complete_func=complete_func,
            complete_shell_var=complete_shell_var,
            complete_script=complete_script,
            script_name=python or self.prog,
        )

    def _shellcode_zsh(self, python: str, module: bool) -> str:
        """Generate the shell code for zsh"""
        complete_shell_var: str = (
            f"{self.progvar}_COMPLETE_SHELL_{self.uid}"
        ).upper()
        complete_script: str = (
            "$words[1]"
            if not python
            else f"$words[1] {self.prog}"
            if not module
            else f"$words[1] -m {self.prog}"
        )
        complete_func: str = f"_{self.progvar}_completion_{self.uid}"
        return COMPLETION_SCRIPT_ZSH % dict(
            complete_func=complete_func,
            complete_shell_var=complete_shell_var,
            complete_script=complete_script,
            script_name=python or self.prog,
        )

    def _get_param_by_prefixed(self, prefixed: str) -> "Param":
        """Get the parameter by the given prefixed name"""
        for param in self._all_params(True):
            if any(
                param._prefix_name(name) == prefixed for name in param.names
            ):
                return param
        return None

    def _parse_completed(
        self,
    ) -> Tuple[List["Param"], bool, str, List[str]]:
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
                return None, None, word, self.comp_words[i + 1 :]

        unmatched_required: bool = False
        matched: List["Param"] = []
        matched_append: Callable = matched.append
        for param in self._all_params(True):
            if any(
                param._prefix_name(name) in self.comp_words
                for name in param.names
            ):
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

    def _complete(self) -> Iterator[Tuple[str, str, str]]:
        """Provide the completion candidates

        The rules are:
        1. When there are uncompleted required parameters, don't give command
           candidates
        2. Otherwise, give both command and parameter candidates
        """
        (
            completed,
            all_required_completed,
            command,
            rest,
        ) = self._parse_completed()

        if command:
            self.commands[command].comp_shell = self.comp_shell
            self.commands[command].comp_words = rest
            self.commands[command].comp_curr = self.comp_curr
            self.commands[command].comp_prev = rest[-1] if rest else None
            # make sure that help parameters or commands are added
            self.commands[command].parse()
            # sys.exit(0)

        completions: Union[
            str,
            Iterator[Tuple[str]],
            Iterator[Tuple[str, str]],
            Iterator[Tuple[str, str, str]],
        ] = ""
        param: "Param" = None
        # see if comp_curr is something like '--arg=x'
        if self.comp_curr and "=" in self.comp_curr:
            prefixed, val = self.comp_curr.split("=", 1)
            param = self._get_param_by_prefixed(prefixed)
            completions = (
                param.complete_value(current=val, prefix=f"{prefixed}=")
                if param
                else completions
            )
        else:
            param = self._get_param_by_prefixed(self.comp_prev)
            completions = (
                param.complete_value(current=self.comp_curr)
                if param
                else completions
            )

        if param:
            if completions is None:
                return  # StopIteration
            if completions is not None and completions:
                for completion in completions:
                    yield (
                        (completion[0], "plain", "")
                        if len(completion) == 1
                        else (
                            completion[0],
                            "plain",
                            completion[1],  # type: ignore
                        )
                        if len(completion) == 2
                        else completion
                    )
                return  # StopIteration, dont go further

        # no param or completions == ''
        for param in self._all_params(True):
            if param.type == "ns":
                continue
            if param in completed and not param.complete_relapse:
                continue

            for prefixed_name, desc in param.complete_name(self.comp_curr):
                yield (prefixed_name, "plain", desc)

        if all_required_completed:
            # see if we have any commands
            for command_name, command in self.commands.items():
                if command_name.startswith(self.comp_curr):
                    yield (
                        command_name,
                        "plain",
                        "Command: " + command.desc[0].splitlines()[0],
                    )


class CompleterParam:
    """Class for a parameter dealing with completion"""

    complete_relapse: bool = False

    def complete_value(
        self, current: str, prefix: str = ""
    ) -> Union[str, Iterator[Tuple[str, ...]]]:
        """Give the completion candidates

        Args:
            current: Current prefix

        Returns:
            None when there are no candidates, nor should we have next
                paramters/commands as candidates (requiring a value).
                An empty string if we should put next parameters/commands
                as candidates. Otherwise yields
                The candidates should be either 1-, 2-, or 3-element tuple.
                If 1-element, type plain and no description implied.
                If 2-element, type plain and 2nd element should be description.
                If 3-element, 2nd element the type, 3rd the description.
        """
        if callable(self.complete_callback):
            return self.complete_callback(current, prefix)
        return None

    def complete_name(self, current: str) -> Iterator[Tuple[str, str]]:
        """Give the completion name candidates

        Args:
            current: The current prefix or word under cursor

        Returns:
            An iterator of a tuple including the prefixed name and description.
        """
        for name in self.names:
            prefixed: str = self._prefix_name(name)
            if prefixed.startswith(current):
                yield (prefixed, self.desc[0].splitlines()[0])
