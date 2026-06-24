from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Project, GeneratedAudio, VoiceSettings

class DashboardView(TemplateView):
    template_name = 'projects/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_projects'] = Project.objects.all().order_by('-updated_at')[:5]
        context['recent_generations'] = GeneratedAudio.objects.all().order_by('-created_at')[:5]
        context['total_projects'] = Project.objects.count()
        context['total_duration'] = sum(float(aud.duration or 0) for aud in GeneratedAudio.objects.filter(status='COMPLETED'))
        context['failed_generations'] = GeneratedAudio.objects.filter(status='FAILED').count()
        return context


class ProjectListView(ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Project.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
        return Project.objects.all().order_by('-updated_at')


class ProjectCreateView(CreateView):
    model = Project
    fields = ['name', 'description']
    template_name = 'projects/project_form.html'
    
    def get_success_url(self):
        return reverse('projects:script_editor', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        # Create default voice settings
        VoiceSettings.objects.get_or_create(
            project=self.object,
            defaults={
                'model_name': "tts_models/en/vctk/vits",
                'speaker_id': "p266",
                'speed': 1.0,
                'pitch': 1.0,
                'output_format': 'wav',
                'output_directory': 'media/generated_audio/'
            }
        )
        messages.success(self.request, f"Project '{self.object.name}' created successfully!")
        return response


class ProjectUpdateView(UpdateView):
    model = Project
    fields = ['name', 'description']
    template_name = 'projects/project_form.html'
    
    def get_success_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Project '{self.object.name}' updated successfully!")
        return response


class ProjectDeleteView(DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('projects:project_list')

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        messages.success(request, f"Project '{project.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['audio_generations'] = self.object.generated_audios.all().order_by('-created_at')
        return context


class ScriptEditorView(DetailView):
    model = Project
    template_name = 'projects/script_editor.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Load voice settings
        context['voice_settings'] = self.object.voice_settings
        # Get historical generation outputs
        context['audio_generations'] = self.object.generated_audios.all().order_by('-created_at')
        # Speakers from VCTK model to choose in dropdown
        context['speakers'] = ["p225", "p226", "p227", "p228", "p232", "p251", "p265", "p266", "p267", "p330"]
        return context


class ImportScriptView(View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if 'script_file' in request.FILES:
            txt_file = request.FILES['script_file']
            if txt_file.name.endswith('.txt'):
                try:
                    file_content = txt_file.read().decode('utf-8')
                    # Create draft audio object with status pending
                    GeneratedAudio.objects.create(
                        project=project,
                        script_text=file_content,
                        speaker=project.voice_settings.speaker_id,
                        status='PENDING'
                    )
                    messages.success(request, "Script imported to generation drafts!")
                except Exception as e:
                    messages.error(request, f"Failed to import file: {str(e)}")
            else:
                messages.error(request, "Invalid file format. Please upload a .txt file.")
        return redirect(reverse('projects:script_editor', kwargs={'pk': project.id}))


class GlobalSettingsView(TemplateView):
    template_name = 'projects/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch the voice settings of the most recent project as a mock global editor
        last_project = Project.objects.first()
        if last_project:
            context['voice_settings'] = last_project.voice_settings
            context['project'] = last_project
        return context

    def post(self, request, *args, **kwargs):
        last_project = Project.objects.first()
        if last_project:
            settings = last_project.voice_settings
            settings.model_name = request.POST.get('model_name', settings.model_name)
            settings.speaker_id = request.POST.get('speaker_id', settings.speaker_id)
            settings.speed = float(request.POST.get('speed', settings.speed))
            settings.pitch = float(request.POST.get('pitch', settings.pitch))
            settings.output_directory = request.POST.get('output_directory', settings.output_directory)
            settings.save()
            messages.success(request, "Global defaults settings updated successfully!")
        else:
            messages.warning(request, "Create at least one project first to set model defaults.")
        return redirect('projects:settings')
