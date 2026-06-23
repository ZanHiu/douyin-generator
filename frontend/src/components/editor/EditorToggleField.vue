<script setup lang="ts">
const props = defineProps<{
  label: string
  description?: string
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function onInput(event: Event) {
  const target = event.target as HTMLInputElement | null
  emit('update:modelValue', Boolean(target?.checked))
}
</script>

<template>
  <label class="editor-form-field editor-form-toggle-field">
    <div class="editor-form-field-head editor-form-field-head-toggle">
      <div class="editor-form-toggle-copy">
        <span class="editor-form-field-label">{{ label }}</span>
        <p v-if="description" class="editor-form-field-description">{{ description }}</p>
      </div>
      <span class="toggle-switch">
        <input :checked="props.modelValue" type="checkbox" @input="onInput" />
        <span class="toggle-slider" aria-hidden="true" />
      </span>
    </div>
  </label>
</template>
