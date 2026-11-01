# License line for the GitHub release descriptions (01.11.2026)

Append the block below, after one blank line, to the end of the GitHub release description of **v2.0.0-alpha22, v2.0.0-alpha23, v2.0.0-beta1 and v2.0.0-beta2**. The same block is already appended to `releases/v2.0.0-alpha13.md` ... `releases/v2.0.0-beta2.md` in the repository (versions released after the 31.10.2026 license transition). Releases before the transition (Python line up to 1.0.0-beta13, Lua 2.0.0-alpha11 and alpha12, whose packages still carried MIT) stay unchanged.

Append without overwriting the published text:

```
for t in v2.0.0-alpha22 v2.0.0-alpha23 v2.0.0-beta1 v2.0.0-beta2; do
  gh release view $t --json body -q .body > body-$t.md
  printf '\n\n' >> body-$t.md
  cat license-block.md >> body-$t.md      # the block below, saved as license-block.md
  gh release edit $t --notes-file body-$t.md
done
```

(Alternatively upload the repository file with `gh release edit <tag> --notes-file releases/<tag>.md`, only if the published body equals that file.)

## Exact block

**License:** [HomenSAI Personal & Commercial Source License v1.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE) — source-available, not open source. Earlier versions released under MIT keep their MIT grant ([LICENSE-MIT-LEGACY](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE-MIT-LEGACY), [details](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSING.md)). Contact: info@homensai.com.

**Лицензия:** [HomenSAI Personal & Commercial Source License v1.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE) — исходный код доступен, но это не open source. Более ранние версии под MIT сохраняют права MIT ([LICENSE-MIT-LEGACY](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE-MIT-LEGACY), [подробнее](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSING.md)). Контакт: info@homensai.com.
