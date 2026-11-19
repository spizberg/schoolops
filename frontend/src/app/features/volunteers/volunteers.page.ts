import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import { Page, Volunteer, VolunteerStatus } from '../../core/models';

@Component({
  selector: 'app-volunteers-page',
  imports: [ReactiveFormsModule],
  templateUrl: './volunteers.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VolunteersPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly volunteers = signal<Volunteer[]>([]);
  readonly total = signal(0);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly editingId = signal<string | null>(null);

  readonly filters = this.fb.nonNullable.group({
    q: [''],
    status: ['' as VolunteerStatus | ''],
  });

  readonly form = this.fb.nonNullable.group({
    first_name: ['', [Validators.required, Validators.maxLength(100)]],
    last_name: ['', [Validators.required, Validators.maxLength(100)]],
    phone: ['', [Validators.required, Validators.maxLength(40)]],
    email: ['', Validators.email],
    joined_on: [''],
  });

  ngOnInit(): void {
    void this.load();
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<Volunteer>>('/volunteers', {
          q: this.filters.controls.q.value,
          status: this.filters.controls.status.value,
          limit: 100,
        }),
      );
      this.volunteers.set(page.items);
      this.total.set(page.total);
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
      ...value,
      email: value.email.trim() || null,
      joined_on: value.joined_on || null,
    };
    try {
      const id = this.editingId();
      if (id) {
        await firstValueFrom(this.api.patch<Volunteer>(`/volunteers/${id}`, payload));
      } else {
        await firstValueFrom(this.api.post<Volunteer>('/volunteers', payload));
      }
      this.cancelEdit();
      await this.load();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  startEdit(volunteer: Volunteer): void {
    this.editingId.set(volunteer.id);
    this.form.setValue({
      first_name: volunteer.first_name,
      last_name: volunteer.last_name,
      phone: volunteer.phone,
      email: volunteer.email ?? '',
      joined_on: volunteer.joined_on ?? '',
    });
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.form.reset({
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      joined_on: '',
    });
  }

  async deactivate(volunteer: Volunteer): Promise<void> {
    if (!globalThis.confirm(`Deactivate ${volunteer.first_name} ${volunteer.last_name}?`)) {
      return;
    }
    this.error.set(null);
    try {
      await firstValueFrom(this.api.delete(`/volunteers/${volunteer.id}`));
      if (this.editingId() === volunteer.id) {
        this.cancelEdit();
      }
      await this.load();
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }
}
