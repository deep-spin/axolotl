"""
monkeypatch to add a get_turns method
"""

import logging
from typing import Generator, Tuple

from fastchat.conversation import SeparatorStyle

LOG = logging.getLogger("axolotl.monkeypatch.fastchat_conversation_turns")


def get_prompt(self) -> str:
    ret = ""
    for role, msg in self.get_turns():
        ret += role + msg
    return ret


def get_turns(  # pylint: disable=too-many-return-statements
    self,
) -> Generator[Tuple[str, str], None, None]:
    """Get the prompt for generation."""
    system_prompt = self.system_template.format(system_message=self.system_message)
    if self.sep_style == SeparatorStyle.ADD_COLON_SINGLE:
        yield "", system_prompt + self.sep
        for role, message in self.messages:
            if message:
                yield role + ": ", message + self.sep
            else:
                yield role + ":", ""
        return
    if self.sep_style == SeparatorStyle.ADD_COLON_TWO:
        seps = [self.sep, self.sep2]
        yield "", system_prompt + seps[0]
        for i, (role, message) in enumerate(self.messages):
            if message:
                yield role + ": ", message + seps[i % 2]
            else:
                yield role + ":", ""
        return
    if self.sep_style == SeparatorStyle.ADD_COLON_SPACE_SINGLE:
        yield "", system_prompt + self.sep
        for role, message in self.messages:
            if message:
                yield role + ": ", message + self.sep
            else:
                yield role + ": ", ""  # must be end with a space
        return
    if self.sep_style == SeparatorStyle.ADD_NEW_LINE_SINGLE:
        yield "", "" if system_prompt == "" else system_prompt + self.sep
        for role, message in self.messages:
            if message:
                yield role + "\n", message + self.sep
            else:
                yield role + "\n", ""
        return
    if self.sep_style == SeparatorStyle.NO_COLON_SINGLE:
        yield "", system_prompt
        for role, message in self.messages:
            if message:
                yield role, message + self.sep
            else:
                yield role, ""
        return
    if self.sep_style == SeparatorStyle.NO_COLON_TWO:
        seps = [self.sep, self.sep2]
        yield "", system_prompt
        for i, (role, message) in enumerate(self.messages):
            if message:
                yield role, message + seps[i % 2]
            else:
                yield role, ""
        return
    if self.sep_style == SeparatorStyle.RWKV:
        yield "", system_prompt
        for i, (role, message) in enumerate(self.messages):
            if message:
                yield role + ": ", message.replace("\r\n", "\n").replace(
                    "\n\n", "\n"
                ) + "\n\n"
            else:
                yield role + ":", ""
        return
    if self.sep_style == SeparatorStyle.LLAMA2 and self.name != "mistral":
        if self.system_message:
            if self.messages:
                # For llama, the system message is incorporated into the first human instruction
                first_role, first_msg = self.messages[0]
                if first_role == self.roles[0]:
                    system_prompt += first_msg
                    self.messages.pop(0)
            yield "", system_prompt
        for i, (role, message) in enumerate(self.messages):
            if message:
                if (i % 2 == 0 and not self.system_message) or (
                    i % 2 != 0 and self.system_message
                ):
                    role = "<s> " + role
                yield role + " ", message
            else:
                yield role, ""
        return
    if self.sep_style == SeparatorStyle.LLAMA2 and self.name == "mistral":
        contains_sys_msg = False
        if self.system_message:
            contains_sys_msg = True
            if self.messages:
                # There is no clear guidance on how to handle system messages in Mistral so we just prepend it to the first human instruction separated by a newline
                first_role, first_msg = self.messages[0]
                if first_role == self.roles[0]:
                    system_prompt = self.system_template.format(
                        system_message=" " + self.system_message
                    )
                    system_prompt += first_msg
                    self.messages.pop(0)
            yield "", system_prompt
        for i, (role, message) in enumerate(self.messages):
            if message and i == 0 and not contains_sys_msg:
                yield "", system_prompt.strip() + " " + message  # if there is no system message, we need to make sure there is the a `<s> [INST]` at the beginning of the first instruction.
            elif message:
                yield role + " ", message
            else:
                yield role, ""
        return
    if self.sep_style == SeparatorStyle.LLAMA3:
        if self.system_message:
            # For llama3, the system message is NOT incorporated into the first human instruction
            # All messages follow <|start_header_id|>' + role + '<|end_header_id|>\n\n'+ message + '<|eot_id|>
            yield "", system_prompt
        for i, (role, message) in enumerate(self.messages):
            if message:
                yield f"<|start_header_id|>{role}<|end_header_id|>\n\n", f"{message.strip()}<|eot_id|>"
            else:
                yield f"<|start_header_id|>{role}<|end_header_id|>\n\n", ""
        return
    if self.sep_style == SeparatorStyle.GEMMA:
        system_message = self.system_message if self.system_message else ""
        first_user_message_processed = False
        
        for i, (role, message) in enumerate(self.messages):
            prefix = "<bos>" if i == 0 else ""
            message_str = message if message else ""
            
            if role == "user" and not first_user_message_processed:
                if system_message:
                    message_str = f"{system_message}\n\n{message_str}"
                first_user_message_processed = True
            
            if message:
                yield prefix + "<start_of_turn>" + role + "\n", message_str + self.sep
            else:
                yield "<start_of_turn>" + role + "\n", ""
        return
    if self.sep_style == SeparatorStyle.CHATGLM:
        # source: https://huggingface.co/THUDM/chatglm-6b/blob/1d240ba371910e9282298d4592532d7f0f3e9f3e/modeling_chatglm.py#L1302-L1308
        # source2: https://huggingface.co/THUDM/chatglm2-6b/blob/e186c891cf64310ac66ef10a87e6635fa6c2a579/modeling_chatglm.py#L926
        round_add_n = 1 if self.name == "chatglm2" else 0
        if system_prompt:
            yield "", system_prompt + self.sep

        for i, (role, message) in enumerate(self.messages):
            if i % 2 == 0:
                yield "", f"[Round {i//2 + round_add_n}]{self.sep}"

            if message:
                yield f"{role}：", f"{message}{self.sep}"
            else:
                yield f"{role}：", ""
        return
    if self.sep_style == SeparatorStyle.CHATML:
        yield "", "" if system_prompt == "" else system_prompt + self.sep + "\n"
        for role, message in self.messages:
            if message:
                yield role + "\n", message + self.sep + "\n"
            else:
                yield role + "\n", ""
        return
    if self.sep_style == SeparatorStyle.CHATGLM3:
        if self.system_message:
            yield "", system_prompt
        for role, message in self.messages:
            if message:
                yield role + "\n", " " + message
            else:
                yield role
        return
    if self.sep_style == SeparatorStyle.CHATINTERN:
        # source: https://huggingface.co/internlm/internlm-chat-7b-8k/blob/bd546fa984b4b0b86958f56bf37f94aa75ab8831/modeling_internlm.py#L771
        seps = [self.sep, self.sep2]
        yield "", system_prompt
        for i, (role, message) in enumerate(self.messages):
            prefix = "<s>" if i % 2 == 0 else ""
            if message:
                yield prefix + role + ":", message + seps[i % 2] + "\n"
            else:
                yield role + ":", ""
        return
    if self.sep_style == SeparatorStyle.DOLLY:
        seps = [self.sep, self.sep2]
        yield "", system_prompt
        for i, (role, message) in enumerate(self.messages):
            if message:
                suffix = "\n\n" if i % 2 == 1 else ""
                yield role + ":\n", message + seps[i % 2] + suffix
            else:
                yield role + ":\n", ""
        return
    if self.sep_style == SeparatorStyle.PHOENIX:
        yield "", system_prompt
        for role, message in self.messages:
            if message:
                yield role + ": ", "<s>" + message + "</s>"
            else:
                yield role + ": " + "<s>", ""
        return
    if self.sep_style == SeparatorStyle.ROBIN:
        yield "", system_prompt + self.sep
        for role, message in self.messages:
            if message:
                yield role + ":\n", message + self.sep
            else:
                yield role + ":\n", ""
        return
    if self.sep_style == SeparatorStyle.FALCON_CHAT:
        if self.system_message:
            yield "", system_prompt + self.sep
        for role, message in self.messages:
            if message:
                yield role + ": ", message + self.sep
            else:
                yield role + ":", ""
    else:
        raise ValueError(f"Invalid style: {self.sep_style}")


def add_get_turns_to_conversation():
    import fastchat.conversation

    fastchat.conversation.Conversation.get_turns = get_turns
    fastchat.conversation.Conversation.get_prompt = get_prompt
