<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">Coming soon</p>
        <h1>{{ title }}</h1>
        <p>{{ description }}</p>
      </div>
    </div>

    <section class="surface empty-workspace">
      <span class="empty-icon">+</span>
      <h2>This workspace is reserved for the next sprint.</h2>
      <p>
        The navigation route is ready so the app can grow without changing the shell again.
      </p>
    </section>
  </section>
</template>
