import { Routes } from '@angular/router';

import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/login/login.page').then((module) => module.LoginPage),
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/dashboard.page').then((module) => module.DashboardPage),
  },
  {
    path: 'ministry-years',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/ministry-years/ministry-years.page').then(
        (module) => module.MinistryYearsPage,
      ),
  },
  {
    path: 'volunteers',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/volunteers/volunteers.page').then(
        (module) => module.VolunteersPage,
      ),
  },
  {
    path: 'children',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/children/children.page').then((module) => module.ChildrenPage),
  },
  {
    path: 'families',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/families/families.page').then((module) => module.FamiliesPage),
  },
  {
    path: 'classes',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/classes/classes.page').then((module) => module.ClassesPage),
  },
  {
    path: 'promotion',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/promotion/promotion.page').then((module) => module.PromotionPage),
  },
  {
    path: 'audit',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/audit/audit.page').then((module) => module.AuditPage),
  },
  {
    path: 'sessions',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/sessions/sessions.page').then((module) => module.SessionsPage),
  },
  { path: '**', redirectTo: 'dashboard' },
];
