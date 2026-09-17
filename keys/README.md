# Module signing key

`module-signing.pem` holds a fixed RSA key and its self-signed certificate. The
build installs it and points `CONFIG_MODULE_SIG_KEY` at it.

## Why it is committed

By default the kernel generates a random key and a certificate dated at
generation time on every build, and embeds the certificate in the Image. That
made two builds from one lock differ by 1,128 bytes. Committing the key removes
that difference.

`certs/Makefile` only generates a key when `CONFIG_MODULE_SIG_KEY` is exactly
`certs/signing_key.pem`. Naming any other file therefore selects the supplied
key and skips generation.

## It is not a secret and not a trust anchor

In this tree the key signs nothing:

- no loadable module is built (`make Image` builds no `.ko`);
- `CONFIG_MODULE_SIG_ALL` is unset, so modules are not signed automatically;
- `CONFIG_MODULE_SIG_FORCE` is unset, so signature enforcement is off and an
  unsigned or foreign-signed module still loads;
- `CONFIG_SYSTEM_TRUSTED_KEYS` is empty, so it anchors nothing.

What it buys is a reproducible Image. It is public, so it proves nothing about
where a module came from.

**If module signature enforcement is ever turned on, replace this key first.**
A public key that is enforced gives a false sense of provenance.

## Replacing it

Generate a new pair with the parameters the kernel uses, update the file, then
refresh `local_files` in every lock:

```sh
openssl req -new -nodes -utf8 -sha256 -days 36500 -batch -x509 \
  -config work/_tmp/ace6-genkey.cnf -outform PEM \
  -out keys/module-signing.pem -keyout keys/module-signing.pem -newkey rsa:4096
```

Each lock records the file's SHA-256, so an edited key fails validation on the
next build rather than silently changing every artifact.
