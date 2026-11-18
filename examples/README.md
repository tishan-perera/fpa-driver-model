# Examples

`draft-commentary.md` is the text returned by `draft_commentary()` for the synthetic model. It is a draft. Nobody has approved it. The tests check that the file still matches the function, so the figures in it are the model's figures.

Generate your own copy, then decide:

```bash
fpa-model run --draft-commentary -o draft.md
fpa-model status draft.md
```
