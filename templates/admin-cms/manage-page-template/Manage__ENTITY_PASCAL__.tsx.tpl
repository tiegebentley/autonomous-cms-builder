import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { Plus, Edit, Trash2, Save, X, {{ICON_NAME}} } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface {{ENTITY_PASCAL}} {
  id: string;
  {{INTERFACE_FIELDS}}
}

export default function Manage{{ENTITY_PLURAL}}() {
  const [items, setItems] = useState<{{ENTITY_PASCAL}}[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<{{ENTITY_PASCAL}} | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toast } = useToast();

  const empty: Omit<{{ENTITY_PASCAL}}, 'id'> = {
    {{EMPTY_FIELDS}}
  };

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      const { data, error } = await supabase
        .from('{{TABLE_NAME}}')
        .select('*')
        .order('{{ORDER_BY}}', { ascending: true });

      if (error) throw error;
      setItems(data || []);
    } catch (error: any) {
      toast({
        title: 'Error loading {{ENTITY_LOWER}}s',
        description: error.message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editing) return;

    try {
      const { id, ...data } = editing;

      if (id) {
        const { error } = await supabase
          .from('{{TABLE_NAME}}')
          .update(data)
          .eq('id', id);
        if (error) throw error;
        toast({ title: '{{ENTITY_PASCAL}} updated' });
      } else {
        const { error } = await supabase
          .from('{{TABLE_NAME}}')
          .insert([data]);
        if (error) throw error;
        toast({ title: '{{ENTITY_PASCAL}} created' });
      }

      setIsDialogOpen(false);
      setEditing(null);
      load();
    } catch (error: any) {
      toast({
        title: 'Error saving {{ENTITY_LOWER}}',
        description: error.message,
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this {{ENTITY_LOWER}}?')) return;
    try {
      const { error } = await supabase
        .from('{{TABLE_NAME}}')
        .delete()
        .eq('id', id);
      if (error) throw error;
      toast({ title: '{{ENTITY_PASCAL}} deleted' });
      load();
    } catch (error: any) {
      toast({
        title: 'Error deleting {{ENTITY_LOWER}}',
        description: error.message,
        variant: 'destructive',
      });
    }
  };

  const openDialog = (item: {{ENTITY_PASCAL}} | null) => {
    setEditing(item || ({ ...empty, id: '' } as {{ENTITY_PASCAL}}));
    setIsDialogOpen(true);
  };

  const updateField = (field: keyof {{ENTITY_PASCAL}}, value: any) => {
    if (editing) setEditing({ ...editing, [field]: value });
  };

  // Helpers for string[] fields. Builder emits the `{{ARRAY_FIELDS_UNION}}` union
  // based on which interface fields are typed `string[]`. If none, the union is
  // `never` and these helpers are dead code (the form body won't reference them).
  const updateArrayField = (field: {{ARRAY_FIELDS_UNION}}, index: number, value: string) => {
    if (!editing) return;
    const arr = [...(editing[field] as string[])];
    arr[index] = value;
    setEditing({ ...editing, [field]: arr } as {{ENTITY_PASCAL}});
  };

  const addArrayItem = (field: {{ARRAY_FIELDS_UNION}}) => {
    if (!editing) return;
    setEditing({
      ...editing,
      [field]: [...(editing[field] as string[]), ''],
    } as {{ENTITY_PASCAL}});
  };

  const removeArrayItem = (field: {{ARRAY_FIELDS_UNION}}, index: number) => {
    if (!editing) return;
    const arr = (editing[field] as string[]).filter((_, i) => i !== index);
    setEditing({ ...editing, [field]: arr } as {{ENTITY_PASCAL}});
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading {{ENTITY_LOWER}}s…</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{{ENTITY_PLURAL}}</h1>
        </div>
        <Button onClick={() => openDialog(null)}>
          <Plus className="mr-2 h-4 w-4" />
          Add {{ENTITY_PASCAL}}
        </Button>
      </div>

      <div className="grid gap-4">
        {items.map((item) => (
          <div key={item.id} className="bg-white p-6 rounded-lg shadow border border-gray-200">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                {{LIST_CARD_BODY}}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => openDialog(item)}>
                  <Edit className="h-4 w-4" />
                </Button>
                <Button variant="destructive" size="sm" onClick={() => handleDelete(item.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editing?.id ? 'Edit {{ENTITY_PASCAL}}' : 'Add New {{ENTITY_PASCAL}}'}
            </DialogTitle>
            <DialogDescription>
              Manage {{ENTITY_LOWER}} details
            </DialogDescription>
          </DialogHeader>

          {editing && (
            <div className="space-y-4">
              {{FORM_BODY}}

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSave}>
                  <Save className="mr-2 h-4 w-4" />
                  Save {{ENTITY_PASCAL}}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
