# Form-Field Fragments

Snippets the builder concatenates into `{{FORM_BODY}}` based on each field's
inferred type. Each fragment assumes `editing`, `updateField`, `updateArrayField`,
`addArrayItem`, `removeArrayItem` are in scope (they always are in the template).

Substitutions per fragment:
- `__FIELD__`       column name (snake_case)
- `__LABEL__`       human label (Title Case)
- `__PLACEHOLDER__` example value

---

## Short text (string)

```tsx
<div>
  <label className="block text-sm font-medium mb-1">__LABEL__</label>
  <Input
    value={editing.__FIELD__}
    onChange={(e) => updateField('__FIELD__', e.target.value)}
    placeholder="__PLACEHOLDER__"
  />
</div>
```

## Long text (string, > 80 chars typical)

```tsx
<div>
  <label className="block text-sm font-medium mb-1">__LABEL__</label>
  <Textarea
    value={editing.__FIELD__}
    onChange={(e) => updateField('__FIELD__', e.target.value)}
    placeholder="__PLACEHOLDER__"
    rows={3}
  />
</div>
```

## Number (integer)

```tsx
<div>
  <label className="block text-sm font-medium mb-1">__LABEL__</label>
  <Input
    type="number"
    value={editing.__FIELD__}
    onChange={(e) => updateField('__FIELD__', parseInt(e.target.value))}
  />
</div>
```

## String array (string[])

```tsx
<div>
  <label className="block text-sm font-medium mb-1">__LABEL__</label>
  {editing.__FIELD__.map((item, index) => (
    <div key={index} className="flex gap-2 mb-2">
      <Input
        value={item}
        onChange={(e) => updateArrayField('__FIELD__', index, e.target.value)}
        placeholder="__PLACEHOLDER__"
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => removeArrayItem('__FIELD__', index)}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  ))}
  <Button
    type="button"
    variant="outline"
    size="sm"
    onClick={() => addArrayItem('__FIELD__')}
  >
    <Plus className="mr-2 h-4 w-4" />
    Add __LABEL__
  </Button>
</div>
```

## Boolean (checkbox)

```tsx
<div className="flex items-center gap-2">
  <input
    type="checkbox"
    id="__FIELD__"
    checked={editing.__FIELD__}
    onChange={(e) => updateField('__FIELD__', e.target.checked)}
  />
  <label htmlFor="__FIELD__" className="text-sm font-medium">__LABEL__</label>
</div>
```

## Image URL (Supabase Storage)

```tsx
<div>
  <label className="block text-sm font-medium mb-1">__LABEL__</label>
  <Input
    value={editing.__FIELD__}
    onChange={(e) => updateField('__FIELD__', e.target.value)}
    placeholder="https://… or upload via Storage"
  />
  {editing.__FIELD__ && (
    <img src={editing.__FIELD__} alt="" className="mt-2 max-h-32 rounded border" />
  )}
</div>
```
