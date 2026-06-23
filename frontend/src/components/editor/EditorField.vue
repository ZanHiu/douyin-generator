<script setup lang="ts">
defineProps<{
  label: string
  value?: string
  description?: string
  wide?: boolean
}>()
</script>

<template>
  <label :class="['editor-form-field', { 'editor-form-field-wide': wide }]">
    <div class="editor-form-field-head">
      <span class="editor-form-field-label">{{ label }}</span>
      <strong v-if="value" class="editor-form-field-value">{{ value }}</strong>
    </div>
    <p v-if="description" class="editor-form-field-description">{{ description }}</p>
    <div class="editor-form-field-control">
      <slot />
    </div>
  </label>
</template>

