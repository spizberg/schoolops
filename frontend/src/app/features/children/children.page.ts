import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import {
  Child,
  ChildGuardian,
  ChildStatus,
  Guardian,
  Household,
  Page,
  PhotoConsent,
} from '../../core/models';

@Component({
  selector: 'app-children-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './children.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChildrenPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly children = signal<Child[]>([]);
  readonly total = signal(0);
  readonly households = signal<Household[]>([]);
  readonly guardians = signal<Guardian[]>([]);
  readonly selectedChild = signal<Child | null>(null);
  readonly guardianLinks = signal<ChildGuardian[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly linkSaving = signal(false);
  readonly error = signal<string | null>(null);
  readonly editingId = signal<string | null>(null);

  readonly filters = this.fb.nonNullable.group({
    q: [''],
    status: ['' as ChildStatus | ''],
    household_id: [''],
  });

  readonly form = this.fb.nonNullable.group({
    first_name: ['', [Validators.required, Validators.maxLength(100)]],
    last_name: ['', [Validators.required, Validators.maxLength(100)]],
    date_of_birth: ['', Validators.required],
    household_id: [''],
    grade: [''],
    allergies: [''],
    medical_notes: [''],
    photo_consent: ['not_recorded' as PhotoConsent, Validators.required],
    status: ['active' as ChildStatus, Validators.required],
    joined_on: [''],
    notes: [''],
  });

  readonly linkForm = this.fb.nonNullable.group({
    guardian_id: ['', Validators.required],
    relationship: ['', [Validators.required, Validators.maxLength(50)]],
    is_primary: false,
    is_emergency: false,
  });

  ngOnInit(): void {
    void this.bootstrap();
  }

  async bootstrap(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const [households, guardians] = await Promise.all([
        firstValueFrom(this.api.get<Page<Household>>('/households', { limit: 100 })),
        firstValueFrom(this.api.get<Page<Guardian>>('/guardians', { limit: 100 })),
      ]);
      this.households.set(households.items);
      this.guardians.set(guardians.items);
      await this.load();
    } catch (error) {
      this.error.set(errorMessage(error));
      this.loading.set(false);
    }
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<Child>>('/children', {
          q: this.filters.controls.q.value,
          status: this.filters.controls.status.value,
          household_id: this.filters.controls.household_id.value,
          limit: 100,
        }),
      );
      this.children.set(page.items);
      this.total.set(page.total);
      const selectedId = this.selectedChild()?.id;
      if (selectedId) {
        const refreshed = page.items.find((item) => item.id === selectedId);
        if (refreshed) {
          this.selectedChild.set(refreshed);
        }
      }
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const value = this.form.getRawValue();
    const payload = {
      first_name: value.first_name,
      last_name: value.last_name,
      date_of_birth: value.date_of_birth,
      household_id: value.household_id || null,
      grade: value.grade.trim() || null,
      allergies: value.allergies.trim() || null,
      medical_notes: value.medical_notes.trim() || null,
      photo_consent: value.photo_consent,
      status: value.status,
      joined_on: value.joined_on || null,
      notes: value.notes.trim() || null,
    };
    try {
      const id = this.editingId();
      if (id) {
        await firstValueFrom(this.api.patch<Child>(`/children/${id}`, payload));
      } else {
        await firstValueFrom(this.api.post<Child>('/children', payload));
      }
      this.cancelEdit();
      await this.load();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  startEdit(child: Child): void {
    this.editingId.set(child.id);
    this.form.setValue({
      first_name: child.first_name,
      last_name: child.last_name,
      date_of_birth: child.date_of_birth,
      household_id: child.household_id ?? '',
      grade: child.grade ?? '',
      allergies: child.allergies ?? '',
      medical_notes: child.medical_notes ?? '',
      photo_consent: child.photo_consent,
      status: child.status,
      joined_on: child.joined_on ?? '',
      notes: child.notes ?? '',
    });
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.form.reset({
      first_name: '',
      last_name: '',
      date_of_birth: '',
      household_id: '',
      grade: '',
      allergies: '',
      medical_notes: '',
      photo_consent: 'not_recorded',
      status: 'active',
      joined_on: '',
      notes: '',
    });
  }

  async selectChild(child: Child): Promise<void> {
    this.selectedChild.set(child);
    this.cancelLink();
    await this.loadGuardianLinks();
  }

  async loadGuardianLinks(): Promise<void> {
    const child = this.selectedChild();
    if (!child) {
      return;
    }
    try {
      const links = await firstValueFrom(
        this.api.get<ChildGuardian[]>(`/children/${child.id}/guardians`),
      );
      this.guardianLinks.set(links);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async saveLink(): Promise<void> {
    const child = this.selectedChild();
    if (!child || this.linkForm.invalid) {
      this.linkForm.markAllAsTouched();
      return;
    }
    this.linkSaving.set(true);
    this.error.set(null);
    try {
      await firstValueFrom(
        this.api.post<ChildGuardian>(
          `/children/${child.id}/guardians`,
          this.linkForm.getRawValue(),
        ),
      );
      this.cancelLink();
      await Promise.all([this.loadGuardianLinks(), this.load()]);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.linkSaving.set(false);
    }
  }

  cancelLink(): void {
    this.linkForm.reset({
      guardian_id: '',
      relationship: '',
      is_primary: false,
      is_emergency: false,
    });
  }

  async setPrimary(link: ChildGuardian): Promise<void> {
    this.error.set(null);
    try {
      await firstValueFrom(
        this.api.post<ChildGuardian>(`/child-guardians/${link.id}/set-primary`, {}),
      );
      await this.loadGuardianLinks();
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async removeLink(link: ChildGuardian): Promise<void> {
    if (!globalThis.confirm(`Remove ${link.guardian.first_name} as a guardian?`)) {
      return;
    }
    this.error.set(null);
    try {
      await firstValueFrom(this.api.delete(`/child-guardians/${link.id}`));
      await Promise.all([this.loadGuardianLinks(), this.load()]);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  householdName(id: string | null): string {
    if (!id) {
      return '—';
    }
    return this.households().find((household) => household.id === id)?.name ?? '—';
  }

  guardianLabel(guardian: Guardian): string {
    return `${guardian.first_name} ${guardian.last_name} (${guardian.phone})`;
  }

  availableGuardians(): Guardian[] {
    const linked = new Set(this.guardianLinks().map((link) => link.guardian_id));
    return this.guardians().filter((guardian) => !linked.has(guardian.id));
  }
}
