# { "Depends": "py-genlayer:test" }

from genlayer import *
import json
import typing


def is_valid_address(address: str) -> bool:
    if not address:
        return False
    if not address.startswith("0x"):
        return False
    if len(address) != 42:
        return False
    valid_chars = "0123456789abcdefABCDEF"
    for char in address[2:]:
        if char not in valid_chars:
            return False
    return True


class MultiKeyVault(gl.Contract):

    secrets:         str   # {"name": "value"} — multiple API keys by name
    owner:           str
    allowed_callers: str
    call_counts:     str   # {"name": count} — per-key call tracking
    rate_limit:      str   # one global limit for all keys
    audit_log:       str
    is_paused:       str
    last_response:   str
    key_version:     str

    def __init__(self, owner_address: str):
        assert is_valid_address(owner_address), "Invalid owner address. Must start with 0x and be 42 characters long."
        self.secrets         = "{}"
        self.owner           = owner_address
        self.allowed_callers = json.dumps([owner_address])
        self.call_counts     = "{}"
        self.rate_limit      = "100"
        self.audit_log       = json.dumps([])
        self.is_paused       = "false"
        self.last_response   = ""
        self.key_version     = "1"

    def _is_owner(self, address: str) -> bool:
        return address == self.owner

    def _log_call(self, action: str, detail: str) -> None:
        log = json.loads(self.audit_log)
        log.append({"action": action, "detail": detail})
        if len(log) > 50:
            log = log[-50:]
        self.audit_log = json.dumps(log)

    # ── SECRET MANAGEMENT ─────────────────────────────────────────

    @gl.public.write
    def add_key(self, name: str, value: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can add keys."
        assert len(name) >= 2, "Key name must be at least 2 characters."
        assert len(value) >= 8, "Key value must be at least 8 characters."
        secrets = json.loads(self.secrets)
        assert name not in secrets, "Key '" + name + "' already exists. Use update_key to change it."
        secrets[name]    = value
        self.secrets     = json.dumps(secrets, sort_keys=True)
        counts           = json.loads(self.call_counts)
        counts[name]     = 0
        self.call_counts = json.dumps(counts, sort_keys=True)
        self.key_version = str(int(self.key_version) + 1)
        self._log_call("ADD_KEY", name)

    @gl.public.write
    def update_key(self, name: str, new_value: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can update keys."
        assert len(new_value) >= 8, "Key value must be at least 8 characters."
        secrets = json.loads(self.secrets)
        assert name in secrets, "Key '" + name + "' does not exist. Use add_key first."
        secrets[name]    = new_value
        self.secrets     = json.dumps(secrets, sort_keys=True)
        self.key_version = str(int(self.key_version) + 1)
        self._log_call("UPDATE_KEY", name)

    @gl.public.write
    def remove_key(self, name: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can remove keys."
        secrets = json.loads(self.secrets)
        assert name in secrets, "Key '" + name + "' does not exist."
        del secrets[name]
        self.secrets     = json.dumps(secrets, sort_keys=True)
        counts           = json.loads(self.call_counts)
        if name in counts:
            del counts[name]
        self.call_counts = json.dumps(counts, sort_keys=True)
        self._log_call("REMOVE_KEY", name)

    @gl.public.write
    def emergency_wipe(self, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can perform an emergency wipe."
        self.secrets     = "{}"
        self.call_counts = "{}"
        self.is_paused   = "true"
        self.key_version = str(int(self.key_version) + 1)
        self._log_call("EMERGENCY_WIPE", "all keys cleared and vault locked")

    # ── CALLER MANAGEMENT ─────────────────────────────────────────

    @gl.public.write
    def add_allowed_caller(self, caller_address: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can add callers."
        assert is_valid_address(caller_address), "Invalid address: " + caller_address
        callers = json.loads(self.allowed_callers)
        assert caller_address not in callers, caller_address + " is already whitelisted."
        callers.append(caller_address)
        self.allowed_callers = json.dumps(callers)

    @gl.public.write
    def remove_allowed_caller(self, caller_address: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can remove callers."
        callers = json.loads(self.allowed_callers)
        if caller_address not in callers:
            return
        callers.remove(caller_address)
        self.allowed_callers = json.dumps(callers)
        self._log_call("REMOVE_CALLER", caller_address)

    @gl.public.write
    def set_rate_limit(self, limit: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can set the rate limit."
        assert limit.isdigit() and int(limit) >= 1, "Rate limit must be a positive number."
        self.rate_limit = limit

    @gl.public.write
    def reset_call_count(self, name: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can reset call counts."
        secrets = json.loads(self.secrets)
        assert name in secrets, "Key '" + name + "' does not exist."
        counts       = json.loads(self.call_counts)
        counts[name] = 0
        self.call_counts = json.dumps(counts, sort_keys=True)
        self._log_call("RESET_COUNT", name)

    @gl.public.write
    def pause(self, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can pause."
        assert self.is_paused == "false", "Vault is already paused."
        self.is_paused = "true"

    @gl.public.write
    def unpause(self, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the owner can unpause."
        assert self.is_paused == "true", "Vault is not paused."
        self.is_paused = "false"

    @gl.public.write
    def transfer_ownership(self, new_owner: str, owner_address: str) -> typing.Any:
        assert self._is_owner(owner_address), "Access denied. Only the current owner can transfer ownership."
        assert is_valid_address(new_owner), "Invalid address: " + new_owner
        assert new_owner != self.owner, "New owner is the same as current owner."
        old_owner  = self.owner
        self.owner = new_owner
        self._log_call("TRANSFER_OWNERSHIP", old_owner + " -> " + new_owner)

    # ── FETCH METHODS ─────────────────────────────────────────────

    @gl.public.write
    def fetch_with_key(self, key_name: str, url: str) -> typing.Any:
        assert self.is_paused == "false", "Vault is paused. Contact the owner to unpause."
        assert url.startswith("http"), "Invalid URL. Must start with http:// or https://"
        secrets = json.loads(self.secrets)
        assert key_name in secrets, "Key '" + key_name + "' does not exist."
        counts = json.loads(self.call_counts)
        count  = counts.get(key_name, 0)
        limit  = int(self.rate_limit)
        if count >= limit:
            self.last_response = json.dumps({
                "error":  "Rate limit reached for '" + key_name + "' (" + self.rate_limit + " calls).",
                "status": "rate_limited"
            })
            return
        secret = secrets[key_name]

        def fetch() -> str:
            try:
                raw = gl.nondet.web.render(url + secret, mode="text")
                if not raw or raw.strip() == "null":
                    return json.dumps({"error": "API returned empty response.", "status": "unavailable"})
                data = json.loads(raw)
                return json.dumps({"status": "ok", "key_used": key_name, "response": data})
            except Exception:
                return json.dumps({"error": "API call failed.", "status": "error"})

        fresh                = gl.eq_principle.prompt_comparative(fetch, "The outputs represent the same API response. They are equivalent if both show the same error status or the response data matches.")
        self.last_response   = fresh
        counts[key_name]     = count + 1
        self.call_counts     = json.dumps(counts, sort_keys=True)
        self._log_call("FETCH", key_name + " -> " + url)

    @gl.public.write
    def fetch_with_key_param(self, key_name: str, url: str, param_name: str) -> typing.Any:
        assert self.is_paused == "false", "Vault is paused. Contact the owner to unpause."
        assert url.startswith("http"), "Invalid URL. Must start with http:// or https://"
        assert len(param_name) > 0, "Provide the API key parameter name e.g. appid."
        secrets = json.loads(self.secrets)
        assert key_name in secrets, "Key '" + key_name + "' does not exist."
        counts = json.loads(self.call_counts)
        count  = counts.get(key_name, 0)
        limit  = int(self.rate_limit)
        if count >= limit:
            self.last_response = json.dumps({
                "error":  "Rate limit reached for '" + key_name + "' (" + self.rate_limit + " calls).",
                "status": "rate_limited"
            })
            return
        secret = secrets[key_name]
        param  = param_name

        def fetch() -> str:
            try:
                raw = gl.nondet.web.render(url + param + "=" + secret, mode="text")
                if not raw or raw.strip() == "null":
                    return json.dumps({"error": "API returned empty response.", "status": "unavailable"})
                data = json.loads(raw)
                return json.dumps({"status": "ok", "key_used": key_name, "response": data})
            except Exception:
                return json.dumps({"error": "API call failed.", "status": "error"})

        fresh                = gl.eq_principle.prompt_comparative(fetch, "The outputs represent the same API response. They are equivalent if both show the same error status or the response data matches.")
        self.last_response   = fresh
        counts[key_name]     = count + 1
        self.call_counts     = json.dumps(counts, sort_keys=True)
        self._log_call("FETCH_PARAM", key_name + " -> " + url)

    # ── FREE READ METHODS ─────────────────────────────────────────

    @gl.public.view
    def get_security_status(self) -> str:
        secrets = json.loads(self.secrets)
        callers = json.loads(self.allowed_callers)
        return json.dumps({
            "owner":          self.owner,
            "is_paused":      self.is_paused,
            "key_version":    self.key_version,
            "total_keys":     str(len(secrets)),
            "key_names":      list(secrets.keys()),
            "keys_exposed":   "no",
            "total_callers":  str(len(callers)),
            "allowed_callers":callers,
            "rate_limit":     self.rate_limit,
        })

    @gl.public.view
    def list_keys(self) -> str:
        secrets = json.loads(self.secrets)
        counts  = json.loads(self.call_counts)
        result  = []
        for name in secrets:
            result.append({
                "name":            name,
                "calls_made":      str(counts.get(name, 0)),
                "calls_remaining": str(int(self.rate_limit) - counts.get(name, 0)),
            })
        return json.dumps({"total": str(len(result)), "keys": result})

    @gl.public.view
    def get_key_stats(self, name: str) -> str:
        secrets = json.loads(self.secrets)
        if name not in secrets:
            return json.dumps({"error": "Key '" + name + "' does not exist."})
        counts = json.loads(self.call_counts)
        count  = counts.get(name, 0)
        return json.dumps({
            "name":            name,
            "calls_made":      str(count),
            "rate_limit":      self.rate_limit,
            "calls_remaining": str(int(self.rate_limit) - count),
            "key_exposed":     "no",
        })

    @gl.public.view
    def get_whitelist(self) -> str:
        callers = json.loads(self.allowed_callers)
        return json.dumps({"total": str(len(callers)), "callers": callers})

    @gl.public.view
    def is_caller_allowed(self, address: str) -> str:
        if not is_valid_address(address):
            return json.dumps({"error": "Invalid address format.", "address": address, "allowed": False})
        callers = json.loads(self.allowed_callers)
        return json.dumps({"address": address, "allowed": address in callers})

    @gl.public.view
    def get_last_response(self) -> str:
        if not self.last_response:
            return json.dumps({"message": "No API calls made yet.", "hint": "Call fetch_with_key to make your first secure API call."})
        return self.last_response

    @gl.public.view
    def get_audit_log(self) -> str:
        return self.audit_log

    @gl.public.view
    def is_paused_status(self) -> str:
        return json.dumps({
            "paused":  self.is_paused,
            "message": "Vault is paused." if self.is_paused == "true" else "Vault is active.",
        })

    @gl.public.view
    def get_key_version(self) -> str:
        return json.dumps({
            "version": self.key_version,
            "message": "Keys have been updated " + str(int(self.key_version) - 1) + " time(s).",
        })

    @gl.public.view
    def get_owner(self) -> str:
        return json.dumps({"owner": self.owner})

    @gl.public.view
    def get_caller_count(self) -> str:
        callers = json.loads(self.allowed_callers)
        return json.dumps({"count": str(len(callers))})