<script setup lang="ts">
import SidebarNav from './SidebarNav.vue'
</script>

<template>
  <div class="app-layout">
    <SidebarNav />
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>
